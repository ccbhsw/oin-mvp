from __future__ import annotations

import secrets
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


def _request_id() -> str:
    return "oin:request:sha256:" + secrets.token_hex(32)


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
    payload = _signed_payload(_request_id())
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
    payload = _signed_payload(_request_id())
    payload["reason"] = "tampered after signing"
    response = client.post("/v1/takedown", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Signature verification failed"


def test_submit_takedown_replay():
    _replay_cache.clear()
    client = TestClient(app)
    payload = _signed_payload(_request_id())
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
        _request_id(),
        requested_at=datetime(2099, 3, 3, 12, 0, 0, tzinfo=UTC),
    )
    middle = _signed_payload(
        _request_id(),
        requested_at=datetime(2099, 3, 2, 12, 0, 0, tzinfo=UTC),
    )
    oldest = _signed_payload(
        _request_id(),
        requested_at=datetime(2099, 3, 1, 12, 0, 0, tzinfo=UTC),
    )
    for payload in (oldest, newest, middle):
        created = client.post("/v1/takedown", json=payload)
        assert created.status_code == 201

    page = client.get("/v1/takedown", params={"limit": 100, "offset": 0})
    assert page.status_code == 200
    body = page.json()
    ours = [row["request_id"] for row in body["records"] if row["request_id"] in {newest["request_id"], middle["request_id"], oldest["request_id"]}]
    assert ours == [newest["request_id"], middle["request_id"], oldest["request_id"]]
    assert set(body["records"][0].keys()) == {
        "request_id",
        "target_object_id",
        "requested_at",
        "status",
        "action",
    }
    sample = next(row for row in body["records"] if row["request_id"] == newest["request_id"])
    assert "reason" not in sample
    assert "requester_pubkey" not in sample
    assert "jurisdiction" not in sample
    assert "legal_basis" not in sample
    assert "verification_document" not in sample
    assert body["total"] >= 3


def test_submit_takedown_rejects_non_object_id_target():
    _replay_cache.clear()
    client = TestClient(app)
    payload = _signed_payload(_request_id())
    payload["target_object_id"] = "http://169.254.169.254/latest/meta-data/"
    response = client.post("/v1/takedown", json=payload)
    assert response.status_code == 400
    assert "oin:object:sha256" in response.json()["detail"]
