from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.db.mongo import get_db
from app.models.common import serialize_doc
from app.schemas.institution import InstitutionOut

router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.get("", response_model=list[InstitutionOut])
async def list_institutions(_: dict = Depends(get_current_user)):
    return [serialize_doc(item) async for item in get_db().institutions.find().sort("name", 1)]
