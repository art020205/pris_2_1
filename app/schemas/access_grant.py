from datetime import datetime

from pydantic import BaseModel


class AccessGrantCreate(BaseModel):
    granted_to_user_id: str
    expires_at: datetime | None = None


class AccessGrantOut(BaseModel):
    id: str
    document_id: str
    patient_id: str
    granted_to_user_id: str
    granted_by_user_id: str
    access_level: str
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime
