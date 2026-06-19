from datetime import datetime

from pydantic import BaseModel


class InstitutionCreate(BaseModel):
    name: str
    address: str | None = None


class InstitutionOut(InstitutionCreate):
    id: str
    created_at: datetime
    updated_at: datetime
