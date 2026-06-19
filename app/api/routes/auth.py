from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pymongo.errors import DuplicateKeyError

from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.mongo import get_db
from app.models.common import date_to_datetime, now_utc, oid, serialize_doc
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.audit_service import write_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterRequest, request: Request):
    if payload.role == "admin":
        raise HTTPException(status_code=400, detail="Admin users are created by seed")
    if payload.institution_id:
        try:
            institution_id = oid(payload.institution_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid institution_id") from exc
    else:
        institution_id = None
    now = now_utc()
    user = {
        "email": payload.email.lower(),
        "password_hash": hash_password(payload.password),
        "full_name": payload.full_name,
        "role": payload.role.value,
        "is_active": True,
        "specialization": payload.specialization,
        "institution_id": institution_id,
        "license_number": payload.license_number,
        "birth_date": date_to_datetime(date.fromisoformat(payload.birth_date)) if payload.birth_date else None,
        "phone": payload.phone,
        "created_at": now,
        "updated_at": now,
    }
    try:
        result = await get_db().users.insert_one(user)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    user["_id"] = result.inserted_id
    await write_audit("user.registered", actor=user, request=request, target_type="user", target_id=result.inserted_id)
    return serialize_doc(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request):
    user = await get_db().users.find_one({"email": payload.email.lower()})
    if not user or not user.get("is_active") or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(str(user["_id"]), {"role": user["role"]})
    await write_audit("auth.login", actor=user, request=request, target_type="user", target_id=user["_id"])
    return {"access_token": token, "user": serialize_doc(user)}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return serialize_doc(user)
