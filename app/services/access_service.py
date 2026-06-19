from datetime import datetime
from typing import Any

from bson import ObjectId

from app.db.mongo import get_db


async def has_active_grant(document_id: ObjectId, doctor_id: ObjectId) -> bool:
    now = datetime.utcnow()
    grant = await get_db().document_access_grants.find_one(
        {
            "document_id": document_id,
            "granted_to_user_id": doctor_id,
            "revoked_at": None,
            "$or": [{"expires_at": None}, {"expires_at": {"$gt": now}}],
        }
    )
    return grant is not None


async def doctor_has_patient_access(patient_id: ObjectId, doctor_id: ObjectId) -> bool:
    now = datetime.utcnow()
    doc_ids = [
        item["_id"]
        async for item in get_db().medical_documents.find({"patient_id": patient_id, "status": "active"}, {"_id": 1})
    ]
    if not doc_ids:
        return False
    grant = await get_db().document_access_grants.find_one(
        {
            "document_id": {"$in": doc_ids},
            "granted_to_user_id": doctor_id,
            "revoked_at": None,
            "$or": [{"expires_at": None}, {"expires_at": {"$gt": now}}],
        }
    )
    return grant is not None


async def can_access_document(document: dict[str, Any], user: dict[str, Any]) -> bool:
    if user["role"] == "admin":
        return True
    if user["role"] == "patient":
        return document["patient_id"] == user["_id"]
    if user["role"] == "doctor":
        return await has_active_grant(document["_id"], user["_id"])
    return False
