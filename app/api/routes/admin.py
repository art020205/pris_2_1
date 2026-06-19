from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import require_role
from app.core.security import hash_password
from app.db.mongo import get_db
from app.models.common import date_to_datetime, now_utc, oid, serialize_doc
from app.schemas.institution import InstitutionCreate, InstitutionOut
from app.schemas.user import UserOut, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(_: dict = Depends(require_role("admin"))):
    return [serialize_doc(item) async for item in get_db().users.find().sort("created_at", -1)]


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, payload: UserUpdate, admin: dict = Depends(require_role("admin"))):
    try:
        target_id = oid(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid user_id") from exc
    update = payload.model_dump(exclude_unset=True, exclude={"email"})
    if "institution_id" in update and update["institution_id"]:
        update["institution_id"] = oid(update["institution_id"])
    if "birth_date" in update:
        update["birth_date"] = date_to_datetime(update["birth_date"])
    if "role" in update and update["role"] is not None:
        update["role"] = update["role"].value
    if "password" in update:
        update["password_hash"] = hash_password(update.pop("password"))
    update["updated_at"] = now_utc()
    result = await get_db().users.update_one({"_id": target_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    from app.services.audit_service import write_audit

    await write_audit("admin.user_updated", actor=admin, target_type="user", target_id=target_id)
    return serialize_doc(await get_db().users.find_one({"_id": target_id}))


@router.post("/institutions", response_model=InstitutionOut, status_code=201)
async def create_institution(payload: InstitutionCreate, _: dict = Depends(require_role("admin"))):
    now = now_utc()
    document = {**payload.model_dump(), "created_at": now, "updated_at": now}
    result = await get_db().institutions.insert_one(document)
    document["_id"] = result.inserted_id
    return serialize_doc(document)
