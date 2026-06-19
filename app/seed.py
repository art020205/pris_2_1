from pymongo.errors import DuplicateKeyError

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.mongo import get_db
from app.models.common import now_utc


async def seed_admin() -> None:
    settings = get_settings()
    database = get_db()
    now = now_utc()
    admin = {
        "email": settings.admin_email.lower(),
        "password_hash": hash_password(settings.admin_password),
        "full_name": "MediConnect Admin",
        "role": "admin",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    try:
        await database.users.insert_one(admin)
    except DuplicateKeyError:
        await database.users.update_one(
            {"email": settings.admin_email.lower()},
            {"$set": {"role": "admin", "is_active": True, "updated_at": now}},
        )
