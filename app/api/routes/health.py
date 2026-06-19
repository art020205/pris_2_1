from fastapi import APIRouter

from app.core.config import get_settings
from app.db.mongo import get_db
from app.services.storage_service import s3_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def ready():
    await get_db().command("ping")
    s3_client().head_bucket(Bucket=get_settings().s3_bucket_name)
    return {"status": "ready"}
