try:
    from datetime import UTC
except ImportError:
    import datetime as dt
    UTC = dt.timezone.utc, datetime

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

from oin.schema.v1 import InformationObject

CONTENT_HASH = "sha256:" + "a" * 64


def make_object(**overrides) -> InformationObject:
    private_key = overrides.pop("_private_key", Ed25519PrivateKey.generate())
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()
    values = {
        "id": "sha256:" + "b" * 64,
        "content_hash": CONTENT_HASH,
        "type": "webpage",
        "source_uri": "https://example.com/article",
        "issuer_pubkey": public_key,
        "observed_at": datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        "signature": "0" * 128,
        "schema_version": "1.0",
        "supersedes": [],
        "witnesses": [],
        "metadata": {"title": "Example"},
    }
    values.update(overrides)
    obj = InformationObject(**values)
    if "signature" not in overrides:
        obj.sign(private_key)
    return obj


def test_valid_object_creation_all_fields():
    private_key = Ed25519PrivateKey.generate()
    obj = make_object(
        _private_key=private_key,
        type="dataset",
        supersedes=["sha256:" + "c" * 64],
        witnesses=[{"pubkey": "d" * 64, "signature": "e" * 128}],
        metadata={"license": "CC-BY", "count": 3},
    )
    assert obj.type == "dataset"
    assert obj.signature != "0" * 128
    assert obj.verify_signature()


def test_missing_required_fields_rejected():
    with pytest.raises(ValidationError):
        InformationObject(
            id="sha256:" + "b" * 64,
            content_hash=CONTENT_HASH,
            type="webpage",
        )


def test_content_hash_format_rejected():
    with pytest.raises(ValidationError):
        make_object(content_hash="sha256:not-a-hash")


def test_id_format_rejected():
    with pytest.raises(ValidationError):
        make_object(id="not-a-cid")


def test_issuer_pubkey_format_rejected():
    with pytest.raises(ValidationError):
        make_object(issuer_pubkey="not-a-key")


def test_empty_source_uri_rejected():
    with pytest.raises(ValidationError):
        make_object(source_uri="")


def test_unknown_type_rejected():
    with pytest.raises(ValidationError):
        make_object(type="unknown")


def test_signature_verification_passes():
    private_key = Ed25519PrivateKey.generate()
    obj = make_object(_private_key=private_key)
    assert obj.verify_signature() is True


def test_signature_verification_fails_after_tampering():
    private_key = Ed25519PrivateKey.generate()
    obj = make_object(_private_key=private_key)
    obj.metadata["tampered"] = True
    assert obj.verify_signature() is False


def test_oversized_metadata_rejected():
    with pytest.raises(ValidationError):
        make_object(metadata={"payload": "x" * 65530})


def test_oversized_source_uri_rejected():
    with pytest.raises(ValidationError):
        make_object(source_uri="https://example.com/" + "x" * 4090)


def test_compute_id_is_deterministic():
    private_key = Ed25519PrivateKey.generate()
    first = make_object(_private_key=private_key)
    second = make_object(_private_key=private_key)
    assert first.compute_id() == second.compute_id()
    assert first.compute_id().startswith("sha256:")
    assert len(first.compute_id()) == 71


def test_witnesses_require_pubkey_and_signature():
    with pytest.raises(ValidationError):
        make_object(witnesses=[{"pubkey": "a" * 64}])
    with pytest.raises(ValidationError):
        make_object(witnesses=[{"pubkey": "a" * 64, "signature": "bad"}])


def test_supersedes_is_a_list_of_nonempty_strings():
    with pytest.raises(ValidationError):
        make_object(supersedes=[""])
    with pytest.raises(ValidationError):
        make_object(supersedes=[123])


def test_json_schema_output():
    schema = InformationObject.to_json_schema()
    assert schema["title"] == "InformationObject"
    assert "id" in schema["properties"]
    assert "content_hash" in schema["required"]
    assert schema["properties"]["source_uri"]["maxLength"] == 4096
    assert schema["properties"]["type"]["enum"] == [
        "webpage", "pdf", "dataset", "image", "video", "audio", "document",
        "news", "software", "git_repo", "sensor_data", "social_media", "public_record", "other",
    ]
