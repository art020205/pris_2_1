from fastapi import APIRouter, Depends

from app.core.dependencies import require_role
from app.db.mongo import get_db
from app.models.common import oid, serialize_doc
from app.schemas.audit_log import AuditLogOut

router = APIRouter(prefix="/admin/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    actor_user_id: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    _: dict = Depends(require_role("admin")),
):
    query = {}
    if actor_user_id:
        query["actor_user_id"] = oid(actor_user_id)
    if action:
        query["action"] = action
    if target_type:
        query["target_type"] = target_type
    if target_id:
        query["target_id"] = oid(target_id)
    if created_from or created_to:
        from datetime import datetime

        query["created_at"] = {}
        if created_from:
            query["created_at"]["$gte"] = datetime.fromisoformat(created_from)
        if created_to:
            query["created_at"]["$lte"] = datetime.fromisoformat(created_to)
    return [serialize_doc(item) async for item in get_db().audit_logs.find(query).sort("created_at", -1)]
