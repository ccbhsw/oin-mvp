from __future__ import annotations

import base64
import secrets

from fastapi.testclient import TestClient

from oin.api.app import app, ingest, repo
from oin.capture.file_capture import capture_file
from oin.capture.text_capture import capture_text
from oin.timestamp.rfc3161 import local_declaration


def test_text_capture_same_canonical_id_records_conflict():
    token = secrets.token_hex(8)
    first = capture_text(f"first edition of the memo {token}", object_identifier=f"memo-{token}")
    second = capture_text(f"second edition of the memo {token}", object_identifier=f"memo-{token}")
    assert first["canonical_id_provided"] is True
    assert second["canonical_id_provided"] is True
    assert first["object_id"] == second["object_id"]
    assert first["observation_id"] != second["observation_id"]

    created_first = ingest(first["manifest"], first["archive"], timestamp_evidence=local_declaration(first["manifest"]))
    created_second = ingest(second["manifest"], second["archive"], timestamp_evidence=local_declaration(second["manifest"]))
    assert created_first["status"] == "created"
    assert created_second["status"] == "created"
    assert created_second["conflicts_created"]

    conflicts = repo.conflicts_for_object(first["object_id"])
    assert len(conflicts) >= 1


def test_file_capture_without_canonical_id_is_independent():
    token = secrets.token_hex(8)
    png = capture_file(b"\x89PNG\r\n\x1a\n" + token.encode(), "shot-a.png")
    pdf = capture_file(b"%PDF-1.4 " + token.encode() + b"-b", "note-b.pdf")
    assert png["canonical_id_provided"] is False
    assert pdf["canonical_id_provided"] is False
    assert png["object_id"] != pdf["object_id"]
    assert png["content_type"] == "image/png"
    assert pdf["content_type"] == "application/pdf"

    first = ingest(png["manifest"], png["archive"], timestamp_evidence=local_declaration(png["manifest"]))
    second = ingest(pdf["manifest"], pdf["archive"], timestamp_evidence=local_declaration(pdf["manifest"]))
    assert first["status"] == "created"
    assert second["status"] == "created"
    assert repo.conflicts_for_object(png["object_id"]) == []
    assert repo.conflicts_for_object(pdf["object_id"]) == []


def test_text_capture_api_reports_canonical_id_flag():
    client = TestClient(app)
    token = secrets.token_hex(8)
    response = client.post(
        "/v1/captures/text",
        json={"text": f"api text payload {token}", "object_identifier": f"api-memo-{token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["canonical_id_provided"] is True
    assert body["object_id"].startswith("oin:object:sha256:")
    assert body["status"] == "created"


def test_file_capture_api_without_identifier():
    client = TestClient(app)
    token = secrets.token_hex(8)
    payload = base64.b64encode(f"unique-file-bytes-for-api-{token}".encode()).decode("ascii")
    response = client.post(
        "/v1/captures/file",
        json={"content_b64": payload, "filename": "note.txt"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["canonical_id_provided"] is False
    assert body["content_type"] == "text/plain"