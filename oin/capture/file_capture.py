"""Capture a file payload as a signed InformationObject and Observation."""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import Any, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from oin.capture.text_capture import capture_payload

_TYPE_BY_MIME = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
    "image/gif": "image",
    "image/webp": "image",
    "video/mp4": "video",
    "audio/mpeg": "audio",
    "text/plain": "document",
}


def capture_file(
    file_content: bytes,
    filename: str,
    object_identifier: Optional[str] = None,
    private_key: Ed25519PrivateKey | None = None,
) -> dict[str, Any]:
    safe_name = Path(filename or "upload.bin").name or "upload.bin"
    guessed, _ = mimetypes.guess_type(safe_name)
    content_type = guessed or "application/octet-stream"
    info_type = _TYPE_BY_MIME.get(content_type, "other")
    identifier = (object_identifier or "").strip() or None
    source = f"oin:file:{identifier}" if identifier else f"oin:file:{uuid.uuid4()}:{safe_name}"
    return capture_payload(
        file_content,
        content_type=content_type,
        info_type=info_type,
        source_uri=source,
        object_identifier=identifier,
        resource_type="other",
        private_key=private_key,
    )
