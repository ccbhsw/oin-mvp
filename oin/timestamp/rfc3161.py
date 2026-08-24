"""Optional RFC 3161 timestamp evidence adapter. Timestamp evidence is detached from the signed manifest to avoid hash recursion."""

from __future__ import annotations

import base64
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from oin.protocol.core import canonical_json, sha256_prefixed

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc


def local_declaration(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "local-declaration",
        "message_imprint": sha256_prefixed(canonical_json(manifest)),
        "declared_captured_at": manifest["capture"]["captured_at"],
        "warning": "This is an Observer-declared time, not independent third-party timestamp evidence.",
    }


def rfc3161_request(manifest: dict[str, Any]) -> bytes:
    """Generate a DER TSQ for the exact canonical signed manifest using OpenSSL."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source, request = root / "manifest.json", root / "request.tsq"
        source.write_bytes(canonical_json(manifest))
        result = subprocess.run(
            ["openssl", "ts", "-query", "-data", str(source), "-sha256", "-cert", "-out", str(request)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "OpenSSL could not generate RFC 3161 request")
        return request.read_bytes()


def _attach_configured_ca(evidence: dict[str, Any]) -> dict[str, Any]:
    ca_path = os.getenv("OIN_TSA_CA_PEM", "").strip()
    if ca_path and Path(ca_path).is_file():
        evidence = dict(evidence)
        evidence["tsa_ca_pem"] = Path(ca_path).read_text()
    return evidence


def obtain_rfc3161_token(manifest: dict[str, Any], tsa_url: str, timeout_seconds: float = 20.0) -> dict[str, Any]:
    request = rfc3161_request(manifest)
    response = httpx.post(
        tsa_url,
        content=request,
        headers={"Content-Type": "application/timestamp-query", "Accept": "application/timestamp-reply"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    evidence = {
        "kind": "rfc3161",
        "message_imprint": sha256_prefixed(canonical_json(manifest)),
        "tsa_url": tsa_url,
        "token_der_b64": base64.b64encode(response.content).decode("ascii"),
        "verification_note": "Offline verification additionally requires a trusted TSA CA certificate in tsa_ca_pem.",
    }
    return _attach_configured_ca(evidence)


def _parse_captured_at(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_openssl_gen_time(text: str) -> datetime | None:
    match = re.search(r"Time stamp:\s+(.+)", text)
    if match:
        raw = match.group(1).strip()
        for fmt in ("%b %d %H:%M:%S %Y %Z", "%b %d %H:%M:%S %Y GMT"):
            try:
                parsed = datetime.strptime(raw.replace("GMT", "").strip() + " GMT", "%b %d %H:%M:%S %Y %Z")
                return parsed.replace(tzinfo=UTC)
            except Exception:
                try:
                    return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
                except Exception:
                    continue
    match = re.search(r"(?:genTime|GENTime|GeneralizedTime)[:=]\s*([0-9]{14})Z", text, re.I)
    if match:
        return datetime.strptime(match.group(1), "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    match = re.search(r"([0-9]{14})Z", text)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        except Exception:
            return None
    return None


def inspect_rfc3161_token(token_der_b64: str) -> dict[str, Any]:
    raw = base64.b64decode(token_der_b64, validate=True)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        token_path = root / "token.tsr"
        token_path.write_bytes(raw)
        texts: list[str] = []
        for args in (
            ["openssl", "ts", "-reply", "-in", str(token_path), "-text"],
            ["openssl", "ts", "-reply", "-in", str(token_path), "-token_in", "-text"],
        ):
            result = subprocess.run(args, capture_output=True, text=True, check=False)
            blob = (result.stdout or "") + "\n" + (result.stderr or "")
            texts.append(blob)
            parsed = _parse_openssl_gen_time(blob)
            if parsed is not None:
                return {"parseable": True, "tsa_time": parsed.isoformat(), "raw_text": blob}
        return {"parseable": False, "tsa_time": None, "raw_text": "\n".join(texts)}


def rfc3161_evidence_is_valid(manifest: dict[str, Any], evidence: dict[str, Any] | None) -> tuple[bool, str]:
    """Return whether detached evidence is a usable RFC 3161 token for this exact signed manifest."""
    if not evidence:
        return False, "timestamp evidence missing"
    if evidence.get("kind") != "rfc3161":
        return False, f"timestamp kind is {evidence.get('kind') or 'absent'}, rfc3161 required"
    expected = sha256_prefixed(canonical_json(manifest))
    if evidence.get("message_imprint") != expected:
        return False, "RFC 3161 message_imprint does not bind this signed manifest"
    token = evidence.get("token_der_b64")
    if not token:
        return False, "RFC 3161 token_der_b64 missing"
    ca_pem = evidence.get("tsa_ca_pem") or ""
    env_ca = os.getenv("OIN_TSA_CA_PEM", "").strip()
    if not ca_pem and env_ca and Path(env_ca).is_file():
        ca_pem = Path(env_ca).read_text()
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        data_path, token_path, ca_path = root / "manifest.json", root / "token.tsr", root / "tsa-ca.pem"
        data_path.write_bytes(canonical_json(manifest))
        token_path.write_bytes(base64.b64decode(token, validate=True))
        if ca_pem:
            ca_path.write_text(ca_pem)
            for extra in ([], ["-token_in"]):
                result = subprocess.run(
                    [
                        "openssl", "ts", "-verify", "-data", str(data_path),
                        "-in", str(token_path), "-CAfile", str(ca_path), *extra,
                    ],
                    capture_output=True, text=True, check=False,
                )
                if result.returncode == 0:
                    return True, "RFC 3161 token signature and imprint verified"
            return False, (result.stderr or result.stdout or "RFC 3161 openssl verify failed").strip()
    inspected = inspect_rfc3161_token(token)
    if inspected.get("parseable"):
        return True, "RFC 3161 token parsed; trusted TSA CA was not supplied so signature chain was not verified"
    return False, "RFC 3161 token could not be parsed"


def describe_timestamp_evidence(manifest: dict[str, Any], evidence: dict[str, Any] | None) -> dict[str, Any]:
    captured_at = (manifest.get("capture") or {}).get("captured_at")
    if not evidence:
        return {
            "kind": None,
            "status": "NOT_PRESENT",
            "captured_at": captured_at,
            "tsa_time": None,
            "captured_at_vs_tsa": None,
        }
    kind = evidence.get("kind")
    result: dict[str, Any] = {
        "kind": kind,
        "status": kind or "UNKNOWN",
        "captured_at": captured_at,
        "tsa_time": None,
        "captured_at_vs_tsa": None,
    }
    if kind == "local-declaration":
        result["status"] = "DECLARED_ONLY"
        return result
    if kind != "rfc3161":
        result["status"] = "UNSUPPORTED"
        return result
    valid, detail = rfc3161_evidence_is_valid(manifest, evidence)
    result["status"] = "VALID" if valid else "INVALID"
    result["detail"] = detail
    inspected = inspect_rfc3161_token(evidence.get("token_der_b64") or "")
    result["tsa_time"] = inspected.get("tsa_time")
    captured = _parse_captured_at(captured_at) if captured_at else None
    tsa_time = _parse_captured_at(inspected["tsa_time"]) if inspected.get("tsa_time") else None
    if captured is not None and tsa_time is not None:
        delta = abs((captured - tsa_time).total_seconds())
        result["captured_at_vs_tsa"] = {
            "delta_seconds": delta,
            "close": delta <= 300,
            "note": "auxiliary comparison only; not a rejection criterion",
        }
    return result
