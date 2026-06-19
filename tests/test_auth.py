import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def test_register_login_and_me(client):
    user, token = await register_and_login(client, "patient@example.com", "patient")

    assert user["email"] == "patient@example.com"
    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["role"] == "patient"


async def test_register_patient_with_birth_date(client):
    response = await client.post(
        "/auth/register",
        json={
            "email": "patient-birth-date@example.com",
            "password": "password123",
            "full_name": "Patient With Date",
            "role": "patient",
            "birth_date": "2005-02-02",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["birth_date"] == "2005-02-02"
