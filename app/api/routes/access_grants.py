from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.dependencies import get_current_user
from app.db.mongo import get_db
from app.models.common import now_utc, oid, serialize_doc
from app.schemas.access_grant import AccessGrantCreate, AccessGrantOut
from app.services.audit_service import write_audit

router = APIRouter(prefix="/documents/{document_id}/access-grants", tags=["access grants"])


async def document_owned_or_admin(document_id: str, user: dict) -> dict:
    try:
        doc_id = oid(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid document_id") from exc
    document = await get_db().medical_documents.find_one({"_id": doc_id, "status": "active"})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if user["role"] != "admin" and not (user["role"] == "patient" and document["patient_id"] == user["_id"]):
        raise HTTPException(status_code=403, detail="Only owner patient or admin can manage grants")
    return document


@router.post("", response_model=AccessGrantOut, status_code=201)
async def create_grant(document_id: str, payload: AccessGrantCreate, request: Request, user: dict = Depends(get_current_user)):
    document = await document_owned_or_admin(document_id, user)
    try:
        doctor_id = oid(payload.granted_to_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid granted_to_user_id") from exc
    doctor = await get_db().users.find_one({"_id": doctor_id, "role": "doctor", "is_active": True})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    grant = {
        "document_id": document["_id"],
        "patient_id": document["patient_id"],
        "granted_to_user_id": doctor_id,
        "granted_by_user_id": user["_id"],
        "access_level": "read",
        "expires_at": payload.expires_at,
        "revoked_at": None,
        "created_at": now_utc(),
    }
    result = await get_db().document_access_grants.insert_one(grant)
    grant["_id"] = result.inserted_id
    await write_audit("access.granted", actor=user, request=request, target_type="document", target_id=document["_id"])
    return serialize_doc(grant)


@router.get("", response_model=list[AccessGrantOut])
async def list_grants(document_id: str, user: dict = Depends(get_current_user)):
    document = await document_owned_or_admin(document_id, user)
    return [
        serialize_doc(item)
        async for item in get_db().document_access_grants.find({"document_id": document["_id"]}).sort("created_at", -1)
    ]


@router.delete("/{grant_id}", status_code=204)
async def revoke_grant(document_id: str, grant_id: str, request: Request, user: dict = Depends(get_current_user)):
    document = await document_owned_or_admin(document_id, user)
    try:
        grant_oid = oid(grant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid grant_id") from exc
    result = await get_db().document_access_grants.update_one(
        {"_id": grant_oid, "document_id": document["_id"], "revoked_at": None},
        {"$set": {"revoked_at": now_utc()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Grant not found")
    await write_audit("access.revoked", actor=user, request=request, target_type="document", target_id=document["_id"])
    return None
