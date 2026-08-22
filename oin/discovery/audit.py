"""Tamper-evident local audit records for static Discovery Bootstrap imports."""

from __future__ import annotations

import hashlib
import json
import re
try:
    from datetime import UTC
except ImportError:
    import datetime as dt
    UTC = dt.timezone.utc, datetime
from pathlib import Path
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_AUDIT_EVENTS = 512
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_HEX_128 = re.compile(r"^[0-9a-f]{128}$")


class DiscoveryAuditEvent(BaseModel):
    """A node-signed assertion about one locally configured Bootstrap Bundle load."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    event_type: Literal["bootstrap_bundle_loaded"] = "bootstrap_bundle_loaded"
    event_id: str
    source_ref: str = Field(min_length=1, max_length=128)
    bundle_hash: str
    accepted_count: int = Field(ge=0, le=128)
    rejected_count: int = Field(ge=0, le=128)
    active_count: int = Field(ge=0, le=129)
    observed_at: datetime
    previous_event_id: str | None = None
    signer_public_key: str
    signature: str = ""

    @field_validator("event_id", "bundle_hash", "previous_event_id")
    @classmethod
    def validate_hash(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("sha256:") or not _HEX_64.fullmatch(value.removeprefix("sha256:")):
            raise ValueError("hash references must use sha256:<64 lowercase hexadecimal characters>")
        return value

    @field_validator("source_ref")
    @classmethod
    def validate_source_ref(cls, value: str) -> str:
        if value != "configured-bootstrap-file":
            raise ValueError("source_ref must be configured-bootstrap-file")
        return value

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value.astimezone(UTC)

    @field_validator("signer_public_key")
    @classmethod
    def validate_public_key(cls, value: str) -> str:
        if not _HEX_64.fullmatch(value):
            raise ValueError("signer_public_key must be a 32-byte Ed25519 public key encoded as lowercase hex")
        return value

    @field_validator("signature")
    @classmethod
    def validate_signature(cls, value: str) -> str:
        if value and not _HEX_128.fullmatch(value):
            raise ValueError("signature must be a 64-byte Ed25519 signature encoded as lowercase hex")
        return value

    def _identity_payload(self) -> bytes:
        data = self.model_dump(mode="json", exclude={"event_id", "signature"})
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _signing_payload(self) -> bytes:
        data = self.model_dump(mode="json", exclude={"signature"})
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def compute_event_id(self) -> str:
        return f"sha256:{hashlib.sha256(self._identity_payload()).hexdigest()}"

    @classmethod
    def build(
        cls,
        private_key: Ed25519PrivateKey,
        *,
        bundle_hash: str,
        accepted_count: int,
        rejected_count: int,
        active_count: int,
        previous_event_id: str | None,
        now: datetime | None = None,
    ) -> DiscoveryAuditEvent:
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        ).hex()
        provisional = cls(
            event_id="sha256:" + "0" * 64,
            source_ref="configured-bootstrap-file",
            bundle_hash=bundle_hash,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            active_count=active_count,
            observed_at=(now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0),
            previous_event_id=previous_event_id,
            signer_public_key=public_key,
        )
        event = provisional.model_copy(update={"event_id": provisional.compute_event_id()})
        return event.model_copy(update={"signature": private_key.sign(event._signing_payload()).hex()})

    def verify(self) -> bool:
        if self.event_id != self.compute_event_id() or not self.signature:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.signer_public_key)).verify(
                bytes.fromhex(self.signature), self._signing_payload()
            )
        except (InvalidSignature, ValueError, TypeError):
            return False
        return True


class DiscoveryAuditLog:
    """Append-only local JSONL audit log with node-signed, hash-linked events."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def events(self) -> list[DiscoveryAuditEvent]:
        if not self.path.exists():
            return []
        if self.path.stat().st_size > MAX_AUDIT_EVENTS * 2048:
            raise ValueError("discovery audit log exceeds the bounded event storage limit")
        records: list[DiscoveryAuditEvent] = []
        previous_event_id: str | None = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            event = DiscoveryAuditEvent.model_validate_json(line)
            if not event.verify() or event.previous_event_id != previous_event_id:
                raise ValueError("discovery audit log integrity verification failed")
            records.append(event)
            previous_event_id = event.event_id
        if len(records) > MAX_AUDIT_EVENTS:
            raise ValueError("discovery audit log exceeds the maximum event count")
        return records

    def record_bootstrap_load(
        self,
        private_key: Ed25519PrivateKey,
        *,
        bundle_bytes: bytes,
        accepted_count: int,
        rejected_count: int,
        active_count: int,
    ) -> DiscoveryAuditEvent:
        records = self.events()
        bundle_hash = f"sha256:{hashlib.sha256(bundle_bytes).hexdigest()}"
        if records and records[-1].bundle_hash == bundle_hash:
            return records[-1]
        if len(records) >= MAX_AUDIT_EVENTS:
            raise ValueError("discovery audit log is full; archive it before importing another bundle")
        event = DiscoveryAuditEvent.build(
            private_key,
            bundle_hash=bundle_hash,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            active_count=active_count,
            previous_event_id=records[-1].event_id if records else None,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")
        return event


__all__ = ["DiscoveryAuditEvent", "DiscoveryAuditLog", "MAX_AUDIT_EVENTS"]
