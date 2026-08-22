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

from oin.discovery import BootstrapRegistry, OperatorDescriptor


def make_descriptor(*, expires_delta=timedelta(hours=1)):
    key = Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes_raw().hex()
    now = datetime.now(UTC).replace(microsecond=0)
    updated_at = now if expires_delta > timedelta(0) else now - timedelta(seconds=2)
    descriptor = OperatorDescriptor(
        operator_id=OperatorDescriptor.operator_id_for_public_key(public_key),
        public_key=public_key,
        endpoints=["https://operator.example"],
        capabilities=["verify"],
        region="US",
        protocol_version="1",
        updated_at=updated_at,
        expires_at=updated_at + expires_delta if expires_delta > timedelta(0) else now - timedelta(seconds=1),
    )
    descriptor.sign(key)
    return descriptor


def test_add_valid_descriptor():
    registry = BootstrapRegistry()
    descriptor = make_descriptor()
    registry.add_descriptor(descriptor)
    assert registry.get_active_operators() == [descriptor]


def test_reject_invalid_signature():
    registry = BootstrapRegistry()
    descriptor = make_descriptor()
    descriptor.signature = "00" * 64
    with pytest.raises(ValueError, match="invalid"):
        registry.add_descriptor(descriptor)
    assert len(registry) == 0


def test_remove_expired():
    registry = BootstrapRegistry()
    registry.add_descriptor(make_descriptor(expires_delta=timedelta(seconds=-1)))
    registry.add_descriptor(make_descriptor())
    assert registry.remove_expired() == 1
    assert len(registry.get_active_operators()) == 1


def test_export_import_bundle_and_skip_invalid_descriptor():
    source = BootstrapRegistry()
    source.add_descriptor(make_descriptor())
    bundle = source.export_bundle()
    target = BootstrapRegistry()
    assert target.import_bundle(bundle) == 1
    assert len(target) == 1

    payload = __import__("json").loads(bundle)
    payload["descriptors"][0]["signature"] = "00" * 64
    assert target.import_bundle(payload) == 0
    assert len(target) == 1


def test_file_persistence(tmp_path):
    source = BootstrapRegistry()
    source.add_descriptor(make_descriptor())
    path = tmp_path / "bootstrap.json"
    source.save_to_file(path)
    target = BootstrapRegistry()
    assert target.load_from_file(path) == 1
    assert target.export_bundle() == source.export_bundle()
