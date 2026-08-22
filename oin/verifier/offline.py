"""Standalone OIN verification. It never contacts an OIN service."""

from __future__ import annotations

import base64
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from oin.capture.http_capture import response_body_from_archive
from oin.observation.service import verify_manifest
from oin.protocol.core import canonical_json, canonicalize_url, object_id, observer_id, sha256_prefixed
from oin.transparency.merkle import verify_proof


def _verify_timestamp(manifest: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    timestamp = evidence.get("timestamp")
    if not timestamp:
        return {"status": "NOT_PRESENT", "valid": None, "detail": "No external timestamp evidence supplied."}
    expected = sha256_prefixed(canonical_json(manifest))
    if timestamp.get("message_imprint") != expected:
        return {"status": "INVALID", "valid": False, "detail": "Timestamp imprint does not bind this exact manifest."}
    if timestamp.get("kind") == "local-declaration":
        return {"status": "DECLARED_ONLY", "valid": True, "detail": "Hash binding is valid; observer-local time is not third-party evidence."}
    if timestamp.get("kind") != "rfc3161":
        return {"status": "UNSUPPORTED", "valid": None, "detail": "Unknown timestamp evidence kind."}
    token, ca_pem = timestamp.get("token_der_b64"), timestamp.get("tsa_ca_pem")
    if not token or not ca_pem:
        return {"status": "INDETERMINATE", "valid": None, "detail": "RFC 3161 token or trusted TSA CA is missing."}
    try:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_path, token_path, ca_path = root / "manifest.json", root / "token.tsr", root / "tsa-ca.pem"
            data_path.write_bytes(canonical_json(manifest))
            token_path.write_bytes(base64.b64decode(token, validate=True))
            ca_path.write_text(ca_pem)
            result = subprocess.run(
                ["openssl", "ts", "-verify", "-data", str(data_path), "-in", str(token_path), "-token_in", "-CAfile", str(ca_path)],
                capture_output=True, text=True, check=False,
            )
        if result.returncode == 0:
            return {"status": "VALID", "valid": True, "detail": "RFC 3161 token signature and imprint verified."}
        return {"status": "INVALID", "valid": False, "detail": result.stderr.strip() or result.stdout.strip()}
    except Exception as exc:
        return {"status": "ERROR", "valid": False, "detail": str(exc)}


def verify_bundle(directory: str | Path, *, require_timestamp: bool = False) -> dict[str, Any]:
    directory = Path(directory)
    manifest_path = directory / "observation.json"
    if not manifest_path.exists():
        raise FileNotFoundError("observation.json is required")
    manifest = json.loads(manifest_path.read_text())
    extension = manifest.get("content", {}).get("archive_format", "wacz")
    archive_path = directory / f"raw.{extension}"
    result: dict[str, Any] = {"status": "INVALID", "checks": {}, "errors": []}
    if not archive_path.exists():
        result["errors"].append(f"{archive_path.name} is missing")
        return result
    archive = archive_path.read_bytes()
    content = manifest["content"]
    result["checks"]["archive_hash"] = sha256_prefixed(archive) == content.get("archive_hash")
    try:
        raw_body = response_body_from_archive(archive, content["archive_format"])
        result["checks"]["raw_content_hash"] = sha256_prefixed(raw_body) == content.get("raw_content_hash")
        result["checks"]["raw_content_bytes"] = len(raw_body) == content.get("raw_content_bytes")
    except Exception:
        result["checks"]["raw_content_hash"] = False
        result["checks"]["raw_content_bytes"] = False
    signature = verify_manifest(manifest)
    result["checks"]["manifest_id"] = signature["manifest_id_valid"]
    result["checks"]["observer_signature"] = signature["signature_valid"]
    try:
        public = base64.b64decode(manifest["observer"]["public_key"], validate=True)
        result["checks"]["observer_identity"] = observer_id(public) == manifest["observer"]["observer_id"]
    except Exception:
        result["checks"]["observer_identity"] = False
    try:
        obj = manifest["object"]
        result["checks"]["object_identity"] = object_id(canonicalize_url(obj["canonical_url"]), obj["resource_type"]) == obj["object_id"]
        result["checks"]["canonical_url"] = canonicalize_url(obj["canonical_url"]) == obj["canonical_url"]
    except Exception:
        result["checks"]["object_identity"] = False
        result["checks"]["canonical_url"] = False
    evidence_path = directory / "evidence.json"
    evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    timestamp = _verify_timestamp(manifest, evidence)
    result["timestamp"] = timestamp
    if "transparency_proof" in evidence:
        result["checks"]["transparency_log"] = verify_proof(manifest, evidence["transparency_proof"])
    else:
        result["checks"]["transparency_log"] = None
    mandatory = [value is True for key, value in result["checks"].items() if key != "transparency_log"]
    transparency_ok = result["checks"]["transparency_log"] in {True, None}
    timestamp_ok = timestamp["valid"] is True or (not require_timestamp and timestamp["status"] in {"NOT_PRESENT", "DECLARED_ONLY", "INDETERMINATE"})
    result["status"] = "VALID" if all(mandatory) and transparency_ok and timestamp_ok else "INVALID"
    if not result["status"] == "VALID":
        result["errors"].extend(key for key, value in result["checks"].items() if value is False)
    return result
