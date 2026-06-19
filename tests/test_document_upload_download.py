import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def test_patient_uploads_and_downloads_document(client):
    _, token = await register_and_login(client, "patient-upload@example.com", "patient")

    upload = await client.post(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"title": "Blood test", "document_type": "lab_result", "metadata_json": '{"source":"lab"}'},
        files={"file": ("result.txt", b"hemoglobin=140", "text/plain")},
    )

    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert document["file"]["sha256"]
    assert document["file"]["object_key"].startswith("medical-documents/")

    download = await client.get(f"/documents/{document['id']}/download", headers={"Authorization": f"Bearer {token}"})
    assert download.status_code == 200
    assert download.content == b"hemoglobin=140"
