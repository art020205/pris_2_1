from io import BytesIO

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

import app.db.mongo as mongo
import app.api.routes.documents as document_routes
from app.main import app


@pytest_asyncio.fixture
async def client(monkeypatch):
    mongo.client = AsyncMongoMockClient()
    mongo.db = mongo.client["test_mediconnect"]
    storage: dict[str, tuple[bytes, str]] = {}

    def fake_put_object(key: str, body: bytes, content_type: str) -> None:
        storage[key] = (body, content_type)

    def fake_get_object_stream(key: str):
        body, _ = storage[key]
        return BytesIO(body), len(body)

    monkeypatch.setattr(document_routes, "put_object", fake_put_object)
    monkeypatch.setattr(document_routes, "get_object_stream", fake_get_object_stream)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    mongo.client.close()
    mongo.client = None
    mongo.db = None


async def register_and_login(client: AsyncClient, email: str, role: str) -> tuple[dict, str]:
    register_response = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": email.split("@")[0], "role": role},
    )
    assert register_response.status_code == 201, register_response.text
    login_response = await client.post("/auth/login", json={"email": email, "password": "password123"})
    assert login_response.status_code == 200, login_response.text
    payload = login_response.json()
    return payload["user"], payload["access_token"]
