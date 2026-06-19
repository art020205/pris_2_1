import hashlib
import json
import re
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.db.mongo import get_db
from app.models.common import now_utc, oid, serialize_doc
from app.schemas.document import DocumentOut
from app.services.access_service import can_access_document, doctor_has_patient_access
from app.services.audit_service import write_audit
from app.services.storage_service import get_object_stream, put_object

router = APIRouter(prefix="/documents", tags=["documents"])


def safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return cleaned or "file"


def parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


async def get_document_or_404(document_id: str) -> dict:
    try:
        doc_id = oid(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid document_id") from exc
    document = await get_db().medical_documents.find_one({"_id": doc_id, "status": "active"})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    patient_id: str | None = Form(default=None),
    title: str = Form(...),
    description: str | None = Form(default=None),
    document_type: str = Form(...),
    diagnosis: str | None = Form(default=None),
    diagnosis_code: str | None = Form(default=None),
    metadata_json: str | None = Form(default=None),
    user: dict = Depends(get_current_user),
):
    if user["role"] == "patient":
        patient_oid = user["_id"]
    else:
        if not patient_id:
            raise HTTPException(status_code=422, detail="patient_id is required")
        try:
            patient_oid = oid(patient_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid patient_id") from exc
        patient = await get_db().users.find_one({"_id": patient_oid, "role": "patient", "is_active": True})
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        if user["role"] == "doctor" and not await doctor_has_patient_access(patient_oid, user["_id"]):
            raise HTTPException(status_code=403, detail="Doctor has no active patient access")

    try:
        metadata = json.loads(metadata_json) if metadata_json else {}
        if not isinstance(metadata, dict):
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="metadata_json must be a JSON object") from exc

    body = await file.read()
    max_size = get_settings().max_upload_size_mb * 1024 * 1024
    if len(body) > max_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is too large")

    document_id = ObjectId()
    key = f"medical-documents/{patient_oid}/{document_id}/{safe_filename(file.filename or 'file')}"
    sha256 = hashlib.sha256(body).hexdigest()
    content_type = file.content_type or "application/octet-stream"
    put_object(key, body, content_type)

    now = now_utc()
    document = {
        "_id": document_id,
        "patient_id": patient_oid,
        "uploaded_by_user_id": user["_id"],
        "uploaded_by_role": user["role"],
        "institution_id": user.get("institution_id"),
        "title": title,
        "description": description,
        "document_type": document_type,
        "diagnosis": diagnosis,
        "diagnosis_code": diagnosis_code,
        "file": {
            "bucket": get_settings().s3_bucket_name,
            "object_key": key,
            "original_filename": file.filename or "file",
            "content_type": content_type,
            "size_bytes": len(body),
            "sha256": sha256,
        },
        "metadata": metadata,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    await get_db().medical_documents.insert_one(document)
    await write_audit("document.uploaded", actor=user, request=request, target_type="document", target_id=document_id)
    return serialize_doc(document)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    patient_id: str | None = None,
    document_type: str | None = None,
    diagnosis_code: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    user: dict = Depends(get_current_user),
):
    query: dict = {"status": "active"}
    if patient_id:
        query["patient_id"] = oid(patient_id)
    if document_type:
        query["document_type"] = document_type
    if diagnosis_code:
        query["diagnosis_code"] = diagnosis_code
    created_query = {}
    if created_from:
        created_query["$gte"] = parse_dt(created_from)
    if created_to:
        created_query["$lte"] = parse_dt(created_to)
    if created_query:
        query["created_at"] = created_query

    if user["role"] == "patient":
        query["patient_id"] = user["_id"]
    elif user["role"] == "doctor":
        now = datetime.utcnow()
        doc_ids = [
            grant["document_id"]
            async for grant in get_db().document_access_grants.find(
                {
                    "granted_to_user_id": user["_id"],
                    "revoked_at": None,
                    "$or": [{"expires_at": None}, {"expires_at": {"$gt": now}}],
                },
                {"document_id": 1},
            )
        ]
        query["_id"] = {"$in": doc_ids}

    return [serialize_doc(item) async for item in get_db().medical_documents.find(query).sort("created_at", -1)]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: str, request: Request, user: dict = Depends(get_current_user)):
    document = await get_document_or_404(document_id)
    if not await can_access_document(document, user):
        raise HTTPException(status_code=403, detail="No access to document")
    await write_audit("document.metadata_viewed", actor=user, request=request, target_type="document", target_id=document["_id"])
    return serialize_doc(document)


@router.get("/{document_id}/download")
async def download_document(document_id: str, request: Request, user: dict = Depends(get_current_user)):
    document = await get_document_or_404(document_id)
    if not await can_access_document(document, user):
        raise HTTPException(status_code=403, detail="No access to document")
    stream, _ = get_object_stream(document["file"]["object_key"])
    await write_audit("document.downloaded", actor=user, request=request, target_type="document", target_id=document["_id"])
    headers = {"Content-Disposition": f'attachment; filename="{safe_filename(document["file"]["original_filename"])}"'}
    return StreamingResponse(stream, media_type=document["file"]["content_type"], headers=headers)


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, user: dict = Depends(get_current_user)):
    document = await get_document_or_404(document_id)
    if user["role"] != "admin" and not (user["role"] == "patient" and document["patient_id"] == user["_id"]):
        raise HTTPException(status_code=403, detail="Only owner patient or admin can delete")
    await get_db().medical_documents.update_one({"_id": document["_id"]}, {"$set": {"status": "deleted", "updated_at": now_utc()}})
    return None
