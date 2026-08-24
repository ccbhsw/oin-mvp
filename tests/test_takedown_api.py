from __future__ import annotations

from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from oin.api.app import app, _replay_cache
from oin.schema.takedown import TakedownRequest

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc


def _signed_payload(request_id: str, requested_at: datetime | None = None) -> dict:
    private_key = Ed25519PrivateKey.generate()
    pubkey = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()
    req = TakedownRequest(
        request_id=request_id,
        target_object_id="oin:object:sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        requester_pubkey=pubkey,
        reason="copyright infringement",
        requested_at=requested_at or datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        request_type="standard",
        action="hide",
        status="pending",
        jurisdiction="EU",
        legal_basis="GDPR Article 17",
        dispute_deadline=datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC),
        signature="0" * 128,
    )
    req.sign(private_key)
    return req.model_dump(mode="json")


def test_submit_takedown_valid():
    _replay_cache.clear()
    client = TestClient(app)
    payload = _signed_payload("oin:request:sha256:" + "11" * 32)
    response = client.post("/v1/takedown", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    assert body["request_id"] == payload["request_id"]
    stored = client.get(f"/v1/takedown/{payload['request_id']}")
    assert stored.status_code == 200
    assert stored.json()["reason"] == "copyright infringement"


def test_submit_takedown_invalid_signature():
    _replay_cache.clear()
    client = TestClient(app)
    payload = _signed_payload("oin:request:sha256:" + "22" * 32)
    payload["reason"] = "tampered after signing"
    response = client.post("/v1/takedown", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Signature verification failed"


def test_submit_takedown_replay():
    _replay_cache.clear()
    client = TestClient(app)
    payload = _signed_payload("oin:request:sha256:" + "33" * 32)
    first = client.post("/v1/takedown", json=payload)
    assert first.status_code == 201
    second = client.post("/v1/takedown", json=payload)
    assert second.status_code == 409
    assert second.json()["detail"] == "Duplicate request detected"


def test_submit_takedown_invalid_json_schema():
    client = TestClient(app)
    response = client.post("/v1/takedown", json={"reason": "missing required fields"})
    assert response.status_code == 422


def test_list_takedowns_pagination_and_order():
    _replay_cache.clear()
    client = TestClient(app)
    newest = _signed_payload(
        "oin:request:sha256:" + "aa" * 32,
        requested_at=datetime(2026, 12, 3, 12, 0, 0, tzinfo=UTC),
    )
    middle = _signed_payload(
        "oin:request:sha256:" + "bb" * 32,
        requested_at=datetime(2026, 12, 2, 12, 0, 0, tzinfo=UTC),
    )
    oldest = _signed_payload(
        "oin:request:sha256:" + "cc" * 32,
        requested_at=datetime(2026, 12, 1, 12, 0, 0, tzinfo=UTC),
    )
    for payload in (oldest, newest, middle):
        created = client.post("/v1/takedown", json=payload)
        assert created.status_code == 201

    page = client.get("/v1/takedown", params={"limit": 2, "offset": 0})
    assert page.status_code == 200
    body = page.json()
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["total"] >= 3
    assert len(body["records"]) == 2
    assert body["records"][0]["request_id"] == newest["request_id"]
    assert body["records"][1]["request_id"] == middle["request_id"]
    assert set(body["records"][0].keys()) == {
        "request_id",
        "target_object_id",
        "requested_at",
        "status",
        "action",
    }
    assert "reason" not in body["records"][0]
    assert "requester_pubkey" not in body["records"][0]
    assert "jurisdiction" not in body["records"][0]
    assert "legal_basis" not in body["records"][0]
    assert "verification_document" not in body["records"][0]

    second = client.get("/v1/takedown", params={"limit": 2, "offset": 2})
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["records"][0]["request_id"] == oldest["request_id"]
