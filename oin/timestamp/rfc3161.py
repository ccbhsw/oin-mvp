"""Optional RFC 3161 timestamp evidence adapter. Timestamp evidence is detached from the signed manifest to avoid hash recursion."""

from __future__ import annotations

import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from oin.protocol.core import canonical_json, sha256_prefixed


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


def obtain_rfc3161_token(manifest: dict[str, Any], tsa_url: str, timeout_seconds: float = 20.0) -> dict[str, Any]:
    request = rfc3161_request(manifest)
    response = httpx.post(
        tsa_url,
        content=request,
        headers={"Content-Type": "application/timestamp-query", "Accept": "application/timestamp-reply"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return {
        "kind": "rfc3161",
        "message_imprint": sha256_prefixed(canonical_json(manifest)),
        "tsa_url": tsa_url,
        "token_der_b64": base64.b64encode(response.content).decode("ascii"),
        "verification_note": "Offline verification additionally requires a trusted TSA CA certificate in tsa_ca_pem.",
    }
