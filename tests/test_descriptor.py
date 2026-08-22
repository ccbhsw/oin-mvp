try:
    try:
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
except ImportError:
    import datetime as dt
    UTC = dt.timezone.utc, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from oin.discovery import OperatorDescriptor


def make_descriptor(private_key=None, *, expires_delta=timedelta(hours=1)):
    key = private_key or Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes_raw().hex()
    now = datetime.now(UTC).replace(microsecond=0)
    updated_at = now if expires_delta > timedelta(0) else now - timedelta(seconds=2)
    descriptor = OperatorDescriptor(
        operator_id=OperatorDescriptor.operator_id_for_public_key(public_key),
        public_key=public_key,
        endpoints=["https://operator.example/oin", "http://backup.example"],
        capabilities=["capture", "replicate", "verify", "store"],
        region="EU",
        protocol_version="1",
        updated_at=updated_at,
        expires_at=updated_at + expires_delta if expires_delta > timedelta(0) else now - timedelta(seconds=1),
    )
    return key, descriptor


def test_valid_descriptor_creation_and_signing():
    key, descriptor = make_descriptor()
    assert descriptor.operator_id.startswith("oin:operator:sha256:")
    assert descriptor.sign(key)
    assert descriptor.verify_signature()


def test_signature_verification_fails_after_tampering():
    key, descriptor = make_descriptor()
    descriptor.sign(key)
    descriptor.endpoints[0] = "https://tampered.example"
    assert not descriptor.verify_signature()


def test_expired_detection():
    _, descriptor = make_descriptor(expires_delta=timedelta(seconds=-1))
    assert descriptor.is_expired()


def test_endpoint_validation():
    key, descriptor = make_descriptor()
    with pytest.raises(ValidationError):
        OperatorDescriptor(
            **descriptor.model_dump(exclude={"endpoints"}), endpoints=["ftp://operator.example"]
        )
    with pytest.raises(ValidationError):
        OperatorDescriptor(
            **descriptor.model_dump(exclude={"endpoints"}), endpoints=["not-a-url"]
        )


def test_wrong_private_key_is_rejected():
    key, descriptor = make_descriptor()
    with pytest.raises(ValueError):
        descriptor.sign(Ed25519PrivateKey.generate())
