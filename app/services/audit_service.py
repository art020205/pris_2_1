from typing import Any

from bson import ObjectId
from fastapi import Request

from app.db.mongo import get_db
from app.models.common import now_utc


async def write_audit(
    action: str,
    actor: dict[str, Any] | None = None,
    request: Request | None = None,
    target_type: str | None = None,
    target_id: ObjectId | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    await get_db().audit_logs.insert_one(
        {
            "actor_user_id": actor.get("_id") if actor else None,
            "actor_role": actor.get("role") if actor else None,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "ip_address": request.client.host if request and request.client else None,
            "user_agent": request.headers.get("user-agent") if request else None,
            "details": details or {},
            "created_at": now_utc(),
        }
    )
