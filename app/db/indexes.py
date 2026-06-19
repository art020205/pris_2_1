from pymongo import ASCENDING

from app.db.mongo import get_db


async def ensure_indexes() -> None:
    database = get_db()
    await database.users.create_index("email", unique=True)
    await database.users.create_index("role")
    await database.medical_documents.create_index("patient_id")
    await database.medical_documents.create_index("uploaded_by_user_id")
    await database.medical_documents.create_index("document_type")
    await database.medical_documents.create_index("created_at")
    await database.medical_documents.create_index("file.sha256")
    await database.document_access_grants.create_index("document_id")
    await database.document_access_grants.create_index("patient_id")
    await database.document_access_grants.create_index("granted_to_user_id")
    await database.document_access_grants.create_index("revoked_at")
    await database.audit_logs.create_index("actor_user_id")
    await database.audit_logs.create_index("action")
    await database.audit_logs.create_index([("target_type", ASCENDING), ("target_id", ASCENDING)])
    await database.audit_logs.create_index("created_at")
