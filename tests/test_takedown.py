import pytest
from datetime import datetime
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
from pydantic import ValidationError
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from oin.schema import TakedownRequest

def test_takedown_creation_and_signature_valid():
    priv_key = Ed25519PrivateKey.generate()
    pub_key_hex = priv_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    req = TakedownRequest(
        request_id="oin:request:sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        target_object_id="oin:object:sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        requester_pubkey=pub_key_hex,
        reason="copyright infringement",
        requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        request_type="standard",
        action="hide",
        status="pending",
        jurisdiction="EU",
        legal_basis="GDPR Article 17",
        dispute_deadline=datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC),
        signature="0" * 128
    )

    req.sign(priv_key)
    assert req.verify_signature() is True

def test_takedown_signature_invalid_on_tamper():
    priv_key = Ed25519PrivateKey.generate()
    pub_key_hex = priv_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    req = TakedownRequest(
        request_id="oin:request:sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        target_object_id="oin:object:sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        requester_pubkey=pub_key_hex,
        reason="copyright infringement",
        requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        request_type="standard",
        action="hide",
        status="pending",
        jurisdiction="EU",
        legal_basis="GDPR Article 17",
        dispute_deadline=datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC),
        signature="0" * 128
    )

    req.sign(priv_key)
    assert req.verify_signature() is True

    req.reason = "tampered reason"
    assert req.verify_signature() is False

def test_takedown_missing_required_fields():
    with pytest.raises(ValidationError):
        TakedownRequest(
            request_id="oin:request:sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            target_object_id="oin:object:sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            reason="copyright infringement",
            requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
            signature="0" * 128
        )

def test_takedown_optional_fields_null_signing():
    priv_key = Ed25519PrivateKey.generate()
    pub_key_hex = priv_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    req = TakedownRequest(
        request_id="oin:request:sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        target_object_id="oin:object:sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        requester_pubkey=pub_key_hex,
        reason="privacy violation",
        requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        signature="0" * 128
    )

    req.sign(priv_key)
    assert req.verify_signature() is True

    req.jurisdiction = "US"
    assert req.verify_signature() is False

def test_takedown_illegal_content_report_rules():
    priv_key = Ed25519PrivateKey.generate()
    pub_key_hex = priv_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    req = TakedownRequest(
        request_id="oin:request:sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        target_object_id="oin:object:sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        requester_pubkey=pub_key_hex,
        reason="illegal content",
        requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        request_type="illegal_content_report",
        dispute_deadline=None,
        signature="0" * 128
    )
    req.sign(priv_key)
    assert req.verify_signature() is True

    with pytest.raises(ValidationError) as exc_info:
        TakedownRequest(
            request_id="oin:request:sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            target_object_id="oin:object:sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            requester_pubkey=pub_key_hex,
            reason="illegal content",
            requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
            request_type="illegal_content_report",
            dispute_deadline=datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC),
            signature="0" * 128
        )
    assert "dispute_deadline must be None" in str(exc_info.value)

def test_json_schema_export():
    schema = TakedownRequest.to_json_schema()
    assert "properties" in schema
    assert "request_id" in schema["properties"]
    assert "target_object_id" in schema["properties"]
    assert "requester_pubkey" in schema["properties"]
    assert "reason" in schema["properties"]
    assert "requested_at" in schema["properties"]
    assert "request_type" in schema["properties"]
    assert "action" in schema["properties"]
    assert "status" in schema["properties"]
    assert "jurisdiction" in schema["properties"]
    assert "legal_basis" in schema["properties"]
    assert "dispute_deadline" in schema["properties"]
    assert "signature" in schema["properties"]
