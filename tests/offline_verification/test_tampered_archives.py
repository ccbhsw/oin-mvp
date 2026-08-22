from __future__ import annotations

from pathlib import Path

from oin.capture.http_capture import CaptureResult, build_warc
from oin.identity.keys import generate_keypair
from oin.observation.service import build_observation, export_bundle
from oin.verifier.offline import verify_bundle


def warc_capture() -> CaptureResult:
    url = "https://example.org/offline-tamper"
    captured_at = "2026-08-21T10:00:00Z"
    headers = {"content-type": "text/html"}
    body = b"<html>original</html>"
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, warc)


def test_offline_verifier_rejects_container_byte_tampering(tmp_path: Path) -> None:
    key, _ = generate_keypair()
    manifest, archive = build_observation(warc_capture(), key, archive_format="warc")
    export_bundle(tmp_path, manifest, archive + b"x")
    result = verify_bundle(tmp_path)
    assert result["status"] == "INVALID"
    assert result["checks"]["archive_hash"] is False


def test_offline_verifier_rejects_modified_embedded_response_body(tmp_path: Path) -> None:
    key, _ = generate_keypair()
    manifest, archive = build_observation(warc_capture(), key, archive_format="warc")
    tampered = archive.replace(b"original", b"modified", 1)
    export_bundle(tmp_path, manifest, tampered)
    result = verify_bundle(tmp_path)
    assert result["status"] == "INVALID"
    assert result["checks"]["archive_hash"] is False
    assert result["checks"]["raw_content_hash"] is False
