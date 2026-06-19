from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


class UserRole(StrEnum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"


class UserBase(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: UserRole | None = None
    specialization: str | None = None
    institution_id: str | None = None
    license_number: str | None = None
    birth_date: date | None = None
    phone: str | None = None


class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: UserRole = UserRole.patient


class UserUpdate(UserBase):
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


class UserOut(UserBase):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
