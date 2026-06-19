from pydantic import BaseModel, EmailStr

from app.schemas.user import UserOut, UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.patient
    specialization: str | None = None
    institution_id: str | None = None
    license_number: str | None = None
    birth_date: str | None = None
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
