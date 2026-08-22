"""Pydantic v2 schema for OIN InformationObject version 1.0."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime
try:
    from datetime import UTC
except ImportError:
    import datetime as dt
    UTC = dt.timezone.utc
from typing import Any, Literal
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

InformationObjectType = Literal[
    "webpage",
    "pdf",
    "dataset",
    "image",
    "video",
    "audio",
    "document",
    "news",
    "software",
    "git_repo",
    "sensor_data",
    "social_media",
    "public_record",
    "other",
]

_HEX_64 = re.compile(r"^[0-9a-fA-F]{64}$")
_HEX_128 = re.compile(r"^[0-9a-fA-F]{128}$")

class InformationObject(BaseModel):
    """A signed, content-addressed information object."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Content-addressed SHA-256 identifier.")
    content_hash: str = Field(..., description="SHA-256 hash of the represented content.")
    type: InformationObjectType
    source_uri: str = Field(..., max_length=4096)
    issuer_pubkey: str = Field(..., description="Raw Ed25519 public key encoded as hex.")
    observed_at: datetime
    signature: str = Field(..., description="Ed25519 signature encoded as hex.")

    supersedes: list[str] = Field(default_factory=list)
    witnesses: list[dict[str, str]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id_prefix(cls, value: str) -> str:
        if not value.startswith("sha256:"):
            raise ValueError("id must start with 'sha256:'")
        if not _HEX_64.fullmatch(value[7:]):
            raise ValueError("id must contain a 64-character hex hash")
        return value.lower()

    @field_validator("content_hash")
    @classmethod
    def validate_content_hash(cls, value: str) -> str:
        if not _HEX_64.fullmatch(value):
            raise ValueError("content_hash must be exactly 64 hexadecimal characters")
        return value.lower()

    @field_validator("issuer_pubkey")
    @classmethod
    def validate_issuer_pubkey(cls, value: str) -> str:
        if not _HEX_64.fullmatch(value):
            raise ValueError("issuer_pubkey must be exactly 64 hexadecimal characters")
        return value.lower()

    @field_validator("signature")
    @classmethod
    def validate_signature_encoding(cls, value: str) -> str:
        if not _HEX_128.fullmatch(value):
            raise ValueError("signature must be exactly 128 hexadecimal characters")
        return value.lower()

    @field_validator("source_uri")
    @classmethod
    def validate_source_uri(cls, value: str) -> str:
        if not value:
            raise ValueError("source_uri must not be empty")
        return value

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value

    @field_validator("supersedes")
    @classmethod
    def validate_supersedes(cls, value: list[str]) -> list[str]:
        if any(not item for item in value):
            raise ValueError("supersedes entries must be non-empty strings")
        return value

    @field_validator("witnesses")
    @classmethod
    def validate_witnesses(cls, value: list[dict[str, str]]) -> list[dict[str, str]]:
        for witness in value:
            if set(witness) != {"pubkey", "signature"}:
                raise ValueError("each witness must contain exactly pubkey and signature")
            if not isinstance(witness["pubkey"], str) or not _HEX_64.fullmatch(witness["pubkey"]):
                raise ValueError("witness pubkey must be 64 hexadecimal characters")
            if not isinstance(witness["signature"], str) or not _HEX_128.fullmatch(witness["signature"]):
                raise ValueError("witness signature must be 128 hexadecimal characters")
        return value

    @field_validator("metadata")
    @classmethod
    def validate_metadata_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must be JSON serializable") from exc
        if len(encoded.encode("utf-8")) > 65536:
            raise ValueError("metadata JSON serialization must not exceed 65536 bytes")
        return value

    @model_validator(mode="after")
    def validate_id_matches_content(self) -> InformationObject:
        return self

    def _signing_payload(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"signature"})
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_id(self) -> str:
        """Return the deterministic ID derived from the object's identity inputs."""
        identity = "|".join(
            (
                self.content_hash,
                self.source_uri,
                self.issuer_pubkey.lower(),
                self.observed_at.astimezone(UTC).isoformat(),
            )
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(identity).hexdigest()}"

    def sign(self, private_key: Ed25519PrivateKey | bytes) -> str:
        """Sign the object payload, update ``signature``, and return its hex signature."""
        key = _coerce_private_key(private_key)
        public_raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if public_raw.hex() != self.issuer_pubkey.lower():
            raise ValueError("private_key does not correspond to issuer_pubkey")
        signature = key.sign(self._signing_payload()).hex()
        self.signature = signature
        return signature

    def verify_signature(self) -> bool:
        """Return whether the current object payload has a valid issuer signature."""
        try:
            public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.issuer_pubkey))
            public_key.verify(bytes.fromhex(self.signature), self._signing_payload())
        except (TypeError, ValueError):
            return False
        except Exception:
            return False
        return True

    @classmethod
    def to_json_schema(cls) -> dict[str, Any]:
        """Return this model's JSON Schema as a plain dictionary."""
        return cls.model_json_schema()

def _coerce_private_key(private_key: Ed25519PrivateKey | bytes) -> Ed25519PrivateKey:
    if isinstance(private_key, Ed25519PrivateKey):
        return private_key
    if isinstance(private_key, bytes):
        if len(private_key) != 32:
            raise ValueError("raw Ed25519 private keys must be 32 bytes")
        return Ed25519PrivateKey.from_private_bytes(private_key)
    raise TypeError("private_key must be an Ed25519PrivateKey or 32 raw bytes")

__all__ = ["InformationObject", "InformationObjectType"]
