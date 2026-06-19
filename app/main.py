from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import access_grants, admin, audit, auth, documents, health, institutions, users
from app.core.config import get_settings
from app.db.indexes import ensure_indexes
from app.db.mongo import close_mongo, connect_mongo
from app.seed import seed_admin
from app.services.storage_service import ensure_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_mongo()
    await ensure_indexes()
    await seed_admin()
    await ensure_bucket()
    yield
    await close_mongo()


app = FastAPI(title="MediConnect API", version="0.1.0", lifespan=lifespan)

settings = get_settings()
origins = ["*"] if settings.cors_origins == "*" else [item.strip() for item in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(institutions.router)
app.include_router(documents.router)
app.include_router(access_grants.router)
app.include_router(audit.router)
