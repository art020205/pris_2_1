import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def test_doctor_access_requires_active_grant(client):
    patient, patient_token = await register_and_login(client, "patient-access@example.com", "patient")
    doctor, doctor_token = await register_and_login(client, "doctor-access@example.com", "doctor")

    upload = await client.post(
        "/documents",
        headers={"Authorization": f"Bearer {patient_token}"},
        data={"title": "MRI", "document_type": "mri_scan"},
        files={"file": ("mri.dcm", b"dicom-bytes", "application/dicom")},
    )
    document = upload.json()

    hidden = await client.get("/documents", headers={"Authorization": f"Bearer {doctor_token}"})
    assert hidden.status_code == 200
    assert hidden.json() == []

    grant_response = await client.post(
        f"/documents/{document['id']}/access-grants",
        headers={"Authorization": f"Bearer {patient_token}"},
        json={"granted_to_user_id": doctor["id"]},
    )
    assert grant_response.status_code == 201, grant_response.text
    grant = grant_response.json()

    visible = await client.get("/documents", headers={"Authorization": f"Bearer {doctor_token}"})
    assert [item["id"] for item in visible.json()] == [document["id"]]

    download = await client.get(f"/documents/{document['id']}/download", headers={"Authorization": f"Bearer {doctor_token}"})
    assert download.status_code == 200
    assert download.content == b"dicom-bytes"

    revoke = await client.delete(
        f"/documents/{document['id']}/access-grants/{grant['id']}",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    assert revoke.status_code == 204

    hidden_again = await client.get("/documents", headers={"Authorization": f"Bearer {doctor_token}"})
    assert hidden_again.status_code == 200
    assert hidden_again.json() == []
