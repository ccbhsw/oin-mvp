from __future__ import annotations

import copy

from oin.capture.http_capture import CaptureResult, build_wacz, build_warc
from oin.identity.keys import generate_keypair, public_document
from oin.observation.service import build_observation, verify_manifest


def capture() -> CaptureResult:
    url = "https://example.org/signature"
    captured_at = "2026-08-21T10:00:00Z"
    headers = {"content-type": "text/html"}
    body = b"<html>signature</html>"
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, build_wacz(warc, url, captured_at))


def test_valid_and_wrong_observer_key_behavior() -> None:
    signing_key, _ = generate_keypair()
    other_key, _ = generate_keypair()
    manifest, _ = build_observation(capture(), signing_key)
    assert verify_manifest(manifest)["valid"] is True

    wrong_public = copy.deepcopy(manifest)
    wrong_public["observer"] = public_document(other_key)
    assert verify_manifest(wrong_public)["valid"] is False


def test_tampered_signature_is_rejected() -> None:
    signing_key, _ = generate_keypair()
    manifest, _ = build_observation(capture(), signing_key)
    tampered = copy.deepcopy(manifest)
    tampered["signature"]["value"] = tampered["signature"]["value"][::-1]
    assert verify_manifest(tampered)["valid"] is False
