from __future__ import annotations

from oin.capture.http_capture import CaptureResult, build_wacz, build_warc
from oin.identity.keys import generate_keypair
from oin.observation.service import build_observation, verify_archive_binding


def synthetic_capture() -> CaptureResult:
    url = "https://example.org/binding"
    captured_at = "2026-08-21T10:00:00Z"
    headers = {"content-type": "text/html"}
    body = b"<html>authentic body</html>"
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, build_wacz(warc, url, captured_at))


def test_archive_binding_checks_archive_and_embedded_raw_content() -> None:
    key, _ = generate_keypair()
    manifest, archive = build_observation(synthetic_capture(), key)
    checks = verify_archive_binding(manifest, archive)
    assert checks == {"archive_hash": True, "raw_content_hash": True, "raw_content_bytes": True}


def test_archive_binding_rejects_mismatched_raw_content_claim() -> None:
    key, _ = generate_keypair()
    manifest, archive = build_observation(synthetic_capture(), key)
    manifest["content"]["raw_content_hash"] = "sha256:" + "0" * 64
    checks = verify_archive_binding(manifest, archive)
    assert checks["archive_hash"] is True
    assert checks["raw_content_hash"] is False
