"""Creation and verification of the signed OIN Observation core manifest."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from oin.capture.http_capture import CaptureResult, response_body_from_archive
from oin.identity.keys import public_document, sign_json, verify_json
from oin.protocol.core import (
    PROTOCOL_VERSION,
    artifact_ref,
    canonicalize_url,
    object_id,
    observation_id,
    sha256_prefixed,
)


def build_observation(
    capture: CaptureResult,
    private_key: Ed25519PrivateKey,
    *,
    archive_format: str = "wacz",
    resource_type: str = "html",
    semantic_identifiers: dict[str, str] | None = None,
) -> tuple[dict[str, Any], bytes]:
    """Sign the core manifest and return it with the selected raw archive bytes."""
    if archive_format not in {"warc", "wacz"}:
        raise ValueError("archive_format must be warc or wacz")
    archive = capture.wacz if archive_format == "wacz" else capture.warc
    archive_type = "application/wacz" if archive_format == "wacz" else "application/warc"
    canonical_url = canonicalize_url(capture.observed_url)
    public = public_document(private_key)
    manifest: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "object": {
            "object_id": object_id(canonical_url, resource_type),
            "canonical_url": canonical_url,
            "original_url": capture.requested_url,
            "observed_url": capture.observed_url,
            "resource_type": resource_type,
            "semantic_identifiers": semantic_identifiers or {},
        },
        "observer": public,
        "capture": {
            "captured_at": capture.captured_at,
            "capture_method": "http-get",
            "capture_software": "oin.capture.http_capture",
            "capture_software_version": "0.1.0",
            "http_status": capture.http_status,
            "http_headers": capture.http_headers,
            "redirect_chain": capture.redirect_chain,
        },
        "content": {
            "archive_format": archive_format,
            "archive_media_type": archive_type,
            "raw_content_hash": sha256_prefixed(capture.body),
            "raw_content_bytes": len(capture.body),
            "raw_content_reference": "warc:response-payload:0",
            "archive_hash": sha256_prefixed(archive),
            "archive_bytes": len(archive),
            "archive_reference": artifact_ref(sha256_prefixed(archive)),
        },
        "provenance": {
            "capture_agent": "OIN Observer",
            "assertion_scope": "Observer statement authenticity and artifact integrity only; no truth determination.",
        },
    }
    manifest["observation_id"] = observation_id(manifest)
    manifest["signature"] = {
        "algorithm": "Ed25519",
        "signed_fields": "all-fields-except-signature",
        "value": sign_json(private_key, manifest),
    }
    return manifest, archive


def unsigned_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(manifest)
    copied.pop("signature", None)
    return copied


def manifest_for_observation_id(manifest: dict[str, Any]) -> dict[str, Any]:
    copied = unsigned_manifest(manifest)
    copied.pop("observation_id", None)
    return copied


def verify_archive_binding(manifest: dict[str, Any], archive: bytes) -> dict[str, bool]:
    """Verify both the immutable archive container and its declared HTTP response payload."""
    content = manifest.get("content", {})
    checks = {
        "archive_hash": sha256_prefixed(archive) == content.get("archive_hash"),
        "raw_content_hash": False,
        "raw_content_bytes": False,
    }
    try:
        raw_body = response_body_from_archive(archive, content["archive_format"])
        checks["raw_content_hash"] = sha256_prefixed(raw_body) == content.get("raw_content_hash")
        checks["raw_content_bytes"] = len(raw_body) == content.get("raw_content_bytes")
    except Exception:
        pass
    return checks


def verify_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    result = {"manifest_id_valid": False, "signature_valid": False, "errors": []}
    try:
        unsigned = unsigned_manifest(manifest)
        expected = observation_id(manifest_for_observation_id(manifest))
        result["manifest_id_valid"] = expected == manifest.get("observation_id")
        if not result["manifest_id_valid"]:
            result["errors"].append("observation_id does not match canonical unsigned manifest")
        signature = manifest.get("signature", {})
        public_key = manifest.get("observer", {}).get("public_key", "")
        result["signature_valid"] = verify_json(public_key, unsigned, signature.get("value", ""))
        if not result["signature_valid"]:
            result["errors"].append("Ed25519 signature is invalid")
    except Exception as exc:
        result["errors"].append(f"manifest verification error: {exc}")
    result["valid"] = result["manifest_id_valid"] and result["signature_valid"]
    return result


def export_bundle(directory: str | Path, manifest: dict[str, Any], archive: bytes, evidence: dict[str, Any] | None = None) -> Path:
    """Write a self-contained offline verification directory without any OIN-hosted dependency."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    extension = manifest["content"]["archive_format"]
    (directory / "observation.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (directory / f"raw.{extension}").write_bytes(archive)
    (directory / "observer-public.json").write_text(json.dumps(manifest["observer"], indent=2, sort_keys=True) + "\n")
    if evidence:
        (directory / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return directory
