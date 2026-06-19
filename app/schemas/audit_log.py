from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    actor_user_id: str | None = None
    actor_role: str | None = None
    action: str
    target_type: str | None = None
    target_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict[str, Any]
    created_at: datetime
