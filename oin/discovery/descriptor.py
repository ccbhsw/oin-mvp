"""Signed operator descriptors used by the OIN discovery layer."""

from __future__ import annotations

import hashlib
import json
try:
    from datetime import UTC
except ImportError:
    import datetime as dt
    UTC = dt.timezone.utc, datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.networks import AnyHttpUrl


class OperatorDescriptor(BaseModel):
    """A short-lived, self-authenticating description of an OIN operator."""

    model_config = ConfigDict(extra="forbid")

    operator_id: str = Field(min_length=1, max_length=128)
    public_key: str = Field(min_length=64, max_length=64)
    endpoints: list[str] = Field(min_length=1, max_length=8)
    capabilities: list[str] = Field(min_length=1, max_length=32)
    region: str = Field(min_length=2, max_length=32)
    protocol_version: str = Field(min_length=1, max_length=32)
    updated_at: datetime
    expires_at: datetime
    signature: str = ""

    @field_validator("public_key")
    @classmethod
    def validate_public_key(cls, value: str) -> str:
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(value))
        except (ValueError, TypeError):
            raise ValueError("public_key must be a 32-byte Ed25519 public key encoded as hex") from None
        return value.lower()

    @field_validator("endpoints")
    @classmethod
    def validate_endpoints(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("at least one endpoint is required")
        normalized: list[str] = []
        for endpoint in value:
            if len(endpoint) > 2048:
                raise ValueError("each endpoint must not exceed 2048 characters")
            parsed = AnyHttpUrl(endpoint)
            if parsed.scheme not in {"http", "https"}:
                raise ValueError("endpoints must use HTTP or HTTPS")
            normalized.append(str(parsed).rstrip("/"))
        return normalized

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 64 for item in value):
            raise ValueError("capabilities must contain non-empty strings no longer than 64 characters")
        return value

    @field_validator("updated_at", "expires_at")
    @classmethod
    def validate_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("signature")
    @classmethod
    def validate_signature(cls, value: str) -> str:
        if value:
            try:
                if len(bytes.fromhex(value)) != 64:
                    raise ValueError
            except ValueError:
                raise ValueError("signature must be a 64-byte Ed25519 signature encoded as hex") from None
        return value.lower()

    @model_validator(mode="after")
    def validate_temporal_order(self) -> OperatorDescriptor:
        if self.expires_at <= self.updated_at:
            raise ValueError("expires_at must be later than updated_at")
        return self

    @staticmethod
    def operator_id_for_public_key(public_key: str) -> str:
        """Return the canonical deterministic operator ID for a public key."""
        return f"oin:operator:sha256:{hashlib.sha256(bytes.fromhex(public_key)).hexdigest()}"

    def _signing_payload(self) -> bytes:
        data = self.model_dump(mode="json", exclude={"signature"})
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sign(self, private_key: Ed25519PrivateKey | bytes | str) -> str:
        """Sign the descriptor in place and return the signature hex string."""
        key = self._coerce_private_key(private_key)
        derived_public_key = key.public_key().public_bytes_raw().hex()
        if derived_public_key != self.public_key:
            raise ValueError("private_key does not match public_key")
        expected_id = self.operator_id_for_public_key(self.public_key)
        if self.operator_id != expected_id:
            raise ValueError("operator_id does not match public_key")
        self.signature = key.sign(self._signing_payload()).hex()
        return self.signature

    def verify_signature(self) -> bool:
        """Verify the descriptor ID, public key and Ed25519 signature."""
        if not self.signature or self.operator_id != self.operator_id_for_public_key(self.public_key):
            return False
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public_key)).verify(
                bytes.fromhex(self.signature), self._signing_payload()
            )
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False

    def is_expired(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        return self.expires_at <= current.astimezone(UTC)

    @staticmethod
    def _coerce_private_key(private_key: Ed25519PrivateKey | bytes | str) -> Ed25519PrivateKey:
        if isinstance(private_key, Ed25519PrivateKey):
            return private_key
        raw = bytes.fromhex(private_key) if isinstance(private_key, str) else private_key
        if len(raw) != 32:
            raise ValueError("private_key must be a 32-byte Ed25519 seed")
        return Ed25519PrivateKey.from_private_bytes(raw)


__all__ = ["OperatorDescriptor"]
