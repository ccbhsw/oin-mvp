from __future__ import annotations

try:
    from datetime import UTC
except ImportError:
    import datetime as dt
    UTC = dt.timezone.utc, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException
from pydantic import ValidationError

from oin.api import app as api
from oin.discovery import BootstrapRegistry, OperatorDescriptor
from oin.discovery.audit import DiscoveryAuditLog
from oin.discovery.bootstrap import MAX_BUNDLE_BYTES, MAX_BUNDLE_DESCRIPTORS


def configured_discovery(monkeypatch: pytest.MonkeyPatch, tmp_path, private_key: Ed25519PrivateKey) -> None:
    monkeypatch.setattr(api, "observer_key", lambda: private_key)
    monkeypatch.setattr(api, "DISCOVERY_BOOTSTRAP_PATH", tmp_path / "bootstrap.json")
    monkeypatch.setattr(api, "DISCOVERY_AUDIT_PATH", tmp_path / "bootstrap-audit.jsonl")
    monkeypatch.setenv("OIN_DISCOVERY_ENDPOINTS", "https://operator.example")
    monkeypatch.setenv("OIN_DISCOVERY_REGION", "ZZ")
    monkeypatch.setenv("OIN_DISCOVERY_CAPABILITIES", "capture,replication,verification")
    monkeypatch.setenv("OIN_DISCOVERY_DESCRIPTOR_TTL_SECONDS", "3600")


def signed_descriptor(private_key: Ed25519PrivateKey) -> OperatorDescriptor:
    public_key = private_key.public_key().public_bytes_raw().hex()
    now = datetime.now(UTC).replace(microsecond=0)
    descriptor = OperatorDescriptor(
        operator_id=OperatorDescriptor.operator_id_for_public_key(public_key),
        public_key=public_key,
        endpoints=["https://bootstrap.example"],
        capabilities=["verification"],
        region="ZZ",
        protocol_version="oin/0.1",
        updated_at=now,
        expires_at=now + timedelta(hours=1),
    )
    descriptor.sign(private_key)
    return descriptor


def test_descriptor_endpoint_requires_explicit_public_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OIN_DISCOVERY_ENDPOINTS", raising=False)
    monkeypatch.setattr(api, "observer_key", Ed25519PrivateKey.generate)

    with pytest.raises(HTTPException) as exc_info:
        api.get_discovery_descriptor()

    assert exc_info.value.status_code == 503
    assert "unavailable" in str(exc_info.value.detail)


def test_descriptor_endpoint_returns_signed_self_authenticating_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    private_key = Ed25519PrivateKey.generate()
    configured_discovery(monkeypatch, tmp_path, private_key)

    payload = api.get_discovery_descriptor()
    descriptor = OperatorDescriptor.model_validate(payload)

    assert descriptor.verify_signature()
    assert descriptor.is_expired() is False
    assert descriptor.endpoints == ["https://operator.example"]
    assert descriptor.capabilities == ["capture", "replication", "verification"]


def test_peers_endpoint_only_returns_valid_non_expired_descriptors(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    private_key = Ed25519PrivateKey.generate()
    configured_discovery(monkeypatch, tmp_path, private_key)

    valid_peer = signed_descriptor(Ed25519PrivateKey.generate())
    invalid_peer = signed_descriptor(Ed25519PrivateKey.generate())
    invalid_peer.signature = "00" * 64
    bundle = {"version": "1", "descriptors": [valid_peer.model_dump(mode="json"), invalid_peer.model_dump(mode="json")]}
    api.DISCOVERY_BOOTSTRAP_PATH.write_text(__import__("json").dumps(bundle), encoding="utf-8")

    response = api.get_discovery_peers()
    peers = [OperatorDescriptor.model_validate(item) for item in response["descriptors"]]

    assert response["version"] == "1"
    assert len(peers) == 2
    assert all(peer.verify_signature() and not peer.is_expired() for peer in peers)
    assert valid_peer.operator_id in {peer.operator_id for peer in peers}
    events = DiscoveryAuditLog(api.DISCOVERY_AUDIT_PATH).events()
    assert len(events) == 1
    assert events[0].accepted_count == 1
    assert events[0].rejected_count == 1
    assert events[0].verify()


def test_discovery_audit_log_detects_tampering_and_does_not_duplicate_same_bundle(tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    audit_path = tmp_path / "bootstrap-audit.jsonl"
    log = DiscoveryAuditLog(audit_path)
    first = log.record_bootstrap_load(
        private_key,
        bundle_bytes=b'{"descriptors":[]}',
        accepted_count=0,
        rejected_count=0,
        active_count=1,
    )
    second = log.record_bootstrap_load(
        private_key,
        bundle_bytes=b'{"descriptors":[]}',
        accepted_count=0,
        rejected_count=0,
        active_count=1,
    )
    assert second.event_id == first.event_id
    assert len(log.events()) == 1

    audit_path.write_text(audit_path.read_text(encoding="utf-8").replace('"accepted_count":0', '"accepted_count":1'), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        log.events()


def test_peers_endpoint_rejects_oversized_bootstrap_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    private_key = Ed25519PrivateKey.generate()
    configured_discovery(monkeypatch, tmp_path, private_key)
    api.DISCOVERY_BOOTSTRAP_PATH.write_bytes(b"x" * (MAX_BUNDLE_BYTES + 1))

    with pytest.raises(HTTPException) as exc_info:
        api.get_discovery_peers()

    assert exc_info.value.status_code == 503
    assert "invalid" in str(exc_info.value.detail)


def test_bootstrap_rejects_excessive_descriptor_count() -> None:
    registry = BootstrapRegistry()
    with pytest.raises(ValueError, match="descriptors"):
        registry.import_bundle({"descriptors": [{}] * (MAX_BUNDLE_DESCRIPTORS + 1)})


def test_descriptor_rejects_oversized_endpoint_and_capability_lists() -> None:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes_raw().hex()
    values = {
        "operator_id": OperatorDescriptor.operator_id_for_public_key(public_key),
        "public_key": public_key,
        "endpoints": ["https://operator.example"],
        "capabilities": ["verification"],
        "region": "ZZ",
        "protocol_version": "oin/0.1",
        "updated_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
    }
    with pytest.raises(ValidationError):
        OperatorDescriptor(**{**values, "endpoints": ["https://operator.example"] * 9})
    with pytest.raises(ValidationError):
        OperatorDescriptor(**{**values, "capabilities": ["verification"] * 33})
