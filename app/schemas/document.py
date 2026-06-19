from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(StrEnum):
    active = "active"
    deleted = "deleted"


class FileInfo(BaseModel):
    bucket: str
    object_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str


class DocumentOut(BaseModel):
    id: str
    patient_id: str
    uploaded_by_user_id: str
    uploaded_by_role: str
    institution_id: str | None = None
    title: str
    description: str | None = None
    document_type: str
    diagnosis: str | None = None
    diagnosis_code: str | None = None
    file: FileInfo
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
