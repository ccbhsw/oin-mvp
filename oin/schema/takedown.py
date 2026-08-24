from __future__ import annotations

import json
import re
from datetime import datetime, timezone
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from oin.protocol.core import OBJECT_ID_PATTERN

_HEX_64 = re.compile(r'^[0-9a-fA-F]{64}$')
_HEX_128 = re.compile(r'^[0-9a-fA-F]{128}$')

class TakedownRequest(BaseModel):
    request_id: str
    target_object_id: str
    requester_pubkey: str
    reason: str
    requested_at: datetime
    # 请求方声称类型，仅记录，不参与逻辑判断
    request_type: Literal["standard", "illegal_content_report"] = "standard"
    action: Literal["hide", "delete"] = "hide"
    status: Literal["pending", "resolved", "disputed", "rejected"] = "pending"
    jurisdiction: Optional[str] = None
    legal_basis: Optional[str] = None
    dispute_deadline: Optional[datetime] = Field(
        default=None,
        description="10-14 天窗口值仅作为产品设计参考，非法律强制期限，具体期限应由节点运营者根据当地法律自行确定。"
    )
    
    # 核实相关字段
    verified_basis: Optional[Literal["court_order", "regulatory_notice", "law_enforcement_request"]] = None
    verification_document: Optional[str] = None
    verified_by: Optional[str] = None
    post_dispute_record: Optional[str] = None
    
    signature: str

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "oin:request:sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                    "target_object_id": "oin:object:sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                    "requester_pubkey": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                    "reason": "copyright infringement",
                    "requested_at": "2026-08-22T12:00:00Z",
                    "request_type": "standard",
                    "action": "hide",
                    "status": "pending",
                    "jurisdiction": "EU",
                    "legal_basis": "GDPR Article 17",
                    "dispute_deadline": "2026-09-05T12:00:00Z",
                    "verified_basis": "court_order",
                    "verification_document": "https://example.com/order.pdf",
                    "verified_by": "node-admin-01",
                    "signature": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
                }
            ]
        }
    }

    @field_validator("target_object_id")
    @classmethod
    def validate_target_object_id(cls, value: str) -> str:
        match = OBJECT_ID_PATTERN.fullmatch(value)
        if not match:
            raise ValueError("target_object_id must be an OIN object identifier (oin:object:sha256:<64-hex>)")
        return f"oin:object:sha256:{match.group(1).lower()}"

    @field_validator("requester_pubkey")
    @classmethod
    def validate_requester_pubkey(cls, value: str) -> str:
        if not _HEX_64.fullmatch(value):
            raise ValueError("requester_pubkey must be exactly 64 hexadecimal characters")
        return value.lower()

    @field_validator("signature")
    @classmethod
    def validate_signature_encoding(cls, value: str) -> str:
        if not _HEX_128.fullmatch(value):
            raise ValueError("signature must be exactly 128 hexadecimal characters")
        return value.lower()

    @field_validator("requested_at", "dispute_deadline")
    @classmethod
    def validate_datetimes(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("datetime fields must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_takedown_logic(self) -> TakedownRequest:
        # 仅当 verified_basis 有值时，dispute_deadline 才可为 None
        # verified_basis 为 None 时，dispute_deadline 必须有值
        if self.verified_basis is None:
            if self.dispute_deadline is None:
                raise ValueError("dispute_deadline must be provided when verified_basis is None")
        return self

    def _signing_payload(self) -> bytes:
        # Exclude signature, but ensure optional fields are serialized as null when None
        payload = self.model_dump(mode="json", exclude={"signature"}, exclude_unset=False, exclude_none=False)
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def verify_signature(self) -> bool:
        """Return whether the current takedown request payload has a valid requester signature."""
        try:
            public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.requester_pubkey))
            public_key.verify(bytes.fromhex(self.signature), self._signing_payload())
        except (TypeError, ValueError):
            return False
        except Exception:
            return False
        return True

    def sign(self, private_key: Ed25519PrivateKey | bytes) -> str:
        """Sign the takedown request payload, update signature, and return its hex signature."""
        if isinstance(private_key, bytes):
            if len(private_key) != 32:
                raise ValueError("raw Ed25519 private keys must be 32 bytes")
            key = Ed25519PrivateKey.from_private_bytes(private_key)
        elif isinstance(private_key, Ed25519PrivateKey):
            key = private_key
        else:
            raise TypeError("private_key must be an Ed25519PrivateKey or 32 raw bytes")
        
        public_raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        if public_raw.hex() != self.requester_pubkey.lower():
            raise ValueError("private_key does not correspond to requester_pubkey")
        
        signature = key.sign(self._signing_payload()).hex()
        self.signature = signature
        return signature

    @classmethod
    def to_json_schema(cls) -> dict[str, Any]:
        return cls.model_json_schema()

__all__ = ["TakedownRequest"]
