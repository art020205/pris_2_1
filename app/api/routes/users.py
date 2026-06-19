from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.core.security import hash_password
from app.db.mongo import get_db
from app.models.common import date_to_datetime, now_utc, oid, serialize_doc
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(user: dict = Depends(get_current_user)):
    return serialize_doc(user)


@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdate, user: dict = Depends(get_current_user)):
    allowed = payload.model_dump(exclude_unset=True, exclude={"role", "is_active", "email"})
    if "institution_id" in allowed and allowed["institution_id"]:
        try:
            allowed["institution_id"] = oid(allowed["institution_id"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid institution_id") from exc
    if "birth_date" in allowed:
        allowed["birth_date"] = date_to_datetime(allowed["birth_date"])
    if "password" in allowed:
        allowed["password_hash"] = hash_password(allowed.pop("password"))
    allowed["updated_at"] = now_utc()
    await get_db().users.update_one({"_id": user["_id"]}, {"$set": allowed})
    return serialize_doc(await get_db().users.find_one({"_id": user["_id"]}))
