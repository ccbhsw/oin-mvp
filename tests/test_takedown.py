import pytest
from datetime import datetime, timezone
try:
    from datetime import UTC
except ImportError:
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
        request_id="oin:request:sha256:1",
        target_object_id="obj1",
        requester_pubkey=pub_key_hex,
        reason="copyright",
        requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        dispute_deadline=datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC),
        signature="0" * 128
    )

    req.sign(priv_key)
    assert req.verify_signature() is True

    # Tamper reason
    req.reason = "tampered"
    assert req.verify_signature() is False

def test_takedown_logic_verified_basis_and_deadline():
    priv_key = Ed25519PrivateKey.generate()
    pub_key_hex = priv_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    # 1. verified_basis 有值 + dispute_deadline = None -> 合法
    req1 = TakedownRequest(
        request_id="req1", target_object_id="obj1", requester_pubkey=pub_key_hex,
        reason="r1", requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        verified_basis="court_order", dispute_deadline=None, signature="0" * 128
    )
    assert req1.verified_basis == "court_order"
    assert req1.dispute_deadline is None

    # 2. verified_basis 为 None + dispute_deadline = None -> 报错
    with pytest.raises(ValidationError) as exc_info:
        TakedownRequest(
            request_id="req2", target_object_id="obj2", requester_pubkey=pub_key_hex,
            reason="r2", requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
            verified_basis=None, dispute_deadline=None, signature="0" * 128
        )
    assert "dispute_deadline must be provided when verified_basis is None" in str(exc_info.value)

    # 3. request_type 不再影响 dispute_deadline 规则
    # illegal_content_report + verified_basis=None + dispute_deadline=datetime -> 合法
    req3 = TakedownRequest(
        request_id="req3", target_object_id="obj3", requester_pubkey=pub_key_hex,
        reason="r3", requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        request_type="illegal_content_report", verified_basis=None,
        dispute_deadline=datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC),
        signature="0" * 128
    )
    assert req3.request_type == "illegal_content_report"
    assert req3.dispute_deadline is not None

    # 5. verified_basis 有值但 verification_document 为空 -> 合法
    req5 = TakedownRequest(
        request_id="req5", target_object_id="obj5", requester_pubkey=pub_key_hex,
        reason="r5", requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        verified_basis="regulatory_notice", verification_document=None,
        dispute_deadline=None, signature="0" * 128
    )
    assert req5.verified_basis == "regulatory_notice"
    assert req5.verification_document is None

    # 6. verified_by 有值但 verified_basis 为 None -> dispute_deadline 仍必须有值
    with pytest.raises(ValidationError) as exc_info:
        TakedownRequest(
            request_id="req6", target_object_id="obj6", requester_pubkey=pub_key_hex,
            reason="r6", requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
            verified_by="admin", verified_basis=None, dispute_deadline=None, signature="0" * 128
        )
    assert "dispute_deadline must be provided when verified_basis is None" in str(exc_info.value)

def test_takedown_new_fields_signature_lock():
    priv_key = Ed25519PrivateKey.generate()
    pub_key_hex = priv_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()

    # 4. 新字段缺失时按 null 参与签名
    req = TakedownRequest(
        request_id="req_lock", target_object_id="obj_lock", requester_pubkey=pub_key_hex,
        reason="lock", requested_at=datetime(2026, 8, 22, 12, 0, 0, tzinfo=UTC),
        dispute_deadline=datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC),
        signature="0" * 128
    )
    # verified_basis, verification_document, etc. are None
    req.sign(priv_key)
    assert req.verify_signature() is True

    # 篡改后验签失败
    req.verified_basis = "court_order"
    assert req.verify_signature() is False

def test_json_schema_export_new_fields():
    schema = TakedownRequest.to_json_schema()
    props = schema["properties"]
    assert "verified_basis" in props
    assert "verification_document" in props
    assert "verified_by" in props
    assert "post_dispute_record" in props
    assert "request_type" in props
