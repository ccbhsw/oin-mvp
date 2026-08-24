"""Capture a UTF-8 text payload as a signed InformationObject and Observation."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from oin.capture.http_capture import CaptureResult, build_warc, build_wacz
from oin.conflict.service import object_identity
from oin.identity.keys import public_document
from oin.observation.service import build_observation
from oin.protocol.core import utc_now
from oin.schema.v1 import InformationObject

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

MAX_CAPTURE_BYTES = 10 * 1024 * 1024


def _public_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()


def capture_payload(
    content: bytes,
    *,
    content_type: str,
    info_type: str,
    source_uri: str,
    object_identifier: Optional[str] = None,
    resource_type: str = "other",
    private_key: Ed25519PrivateKey | None = None,
) -> dict[str, Any]:
    if len(content) > MAX_CAPTURE_BYTES:
        raise ValueError("payload exceeds 10MB capture limit")
    key = private_key or Ed25519PrivateKey.generate()
    provided = bool(object_identifier and str(object_identifier).strip())
    identifier = str(object_identifier).strip() if provided else None
    object_id = object_identity(canonical_id=identifier, resource_type=resource_type)
    content_hash = hashlib.sha256(content).hexdigest()
    observed_at = datetime.now(UTC)
    info = InformationObject(
        id="sha256:" + "00" * 32,
        content_hash=content_hash,
        type=info_type,  # type: ignore[arg-type]
        source_uri=source_uri,
        issuer_pubkey=_public_hex(key),
        observed_at=observed_at,
        signature="0" * 128,
        content_type=content_type,
        canonical_id=identifier,
    )
    info.id = info.compute_id()
    info.sign(key)

    captured_at = utc_now()
    warc = build_warc(source_uri, captured_at, 200, {"content-type": content_type}, content)
    capture = CaptureResult(
        requested_url=source_uri,
        observed_url=source_uri,
        captured_at=captured_at,
        http_status=200,
        http_headers={"content-type": content_type},
        redirect_chain=[],
        body=content,
        content_type=content_type,
        warc=warc,
        wacz=build_wacz(warc, source_uri, captured_at),
    )
    extras = {"content_type": content_type}
    if identifier:
        extras["canonical_id"] = identifier
    manifest, archive = build_observation(
        capture,
        key,
        archive_format="wacz",
        resource_type=resource_type,
        identity_object_id=object_id,
        object_extras=extras,
    )
    return {
        "object_id": object_id,
        "observation_id": manifest["observation_id"],
        "canonical_id_provided": provided,
        "content_type": content_type,
        "content_hash": content_hash,
        "information_object": info.model_dump(mode="json"),
        "manifest": manifest,
        "archive": archive,
        "observer": public_document(key),
    }


def capture_text(
    text: str,
    object_identifier: Optional[str] = None,
    private_key: Ed25519PrivateKey | None = None,
) -> dict[str, Any]:
    identifier = (object_identifier or "").strip() or None
    source = f"oin:text:{identifier}" if identifier else f"oin:text:independent:{uuid.uuid4()}"
    return capture_payload(
        text.encode("utf-8"),
        content_type="text/plain",
        info_type="document",
        source_uri=source,
        object_identifier=identifier,
        resource_type="other",
        private_key=private_key,
    )
