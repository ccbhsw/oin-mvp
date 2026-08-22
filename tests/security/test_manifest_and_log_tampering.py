from __future__ import annotations

import copy

import pytest

from oin.capture.http_capture import CaptureResult, build_wacz, build_warc
from oin.identity.keys import generate_keypair
from oin.observation.service import build_observation, verify_manifest
from oin.transparency.merkle import MerkleLog, verify_proof


def synthetic_capture() -> CaptureResult:
    url = "https://example.org/tamper"
    captured_at = "2026-08-21T10:00:00Z"
    headers = {"content-type": "text/html"}
    body = b"<html>original</html>"
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, build_wacz(warc, url, captured_at))


@pytest.mark.parametrize(
    "path,value",
    [
        (("object", "canonical_url"), "https://attacker.example/"),
        (("observer", "observer_id"), "oin:observer:sha256:" + "0" * 64),
        (("capture", "captured_at"), "2030-01-01T00:00:00Z"),
        (("content", "raw_content_hash"), "sha256:" + "1" * 64),
        (("content", "archive_hash"), "sha256:" + "2" * 64),
        (("protocol_version",), "999.0"),
        (("signature", "value"), "not-a-valid-signature"),
    ],
)
def test_unsigned_manifest_tampering_is_rejected(path: tuple[str, ...], value: str) -> None:
    key, _ = generate_keypair()
    manifest, _ = build_observation(synthetic_capture(), key)
    tampered = copy.deepcopy(manifest)
    target = tampered
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    assert verify_manifest(tampered)["valid"] is False


def test_log_leaf_or_checkpoint_tampering_is_rejected(tmp_path) -> None:
    key, _ = generate_keypair()
    manifest, _ = build_observation(synthetic_capture(), key)
    log = MerkleLog(tmp_path / "log")
    log.append(manifest)
    proof = log.proof(manifest["observation_id"])
    assert proof is not None and verify_proof(manifest, proof)

    tampered_leaf = copy.deepcopy(proof)
    tampered_leaf["entry"]["manifest_hash"] = "sha256:" + "00" * 32
    assert verify_proof(manifest, tampered_leaf) is False

    tampered_checkpoint = copy.deepcopy(proof)
    tampered_checkpoint["checkpoint"]["signature"] = "invalid"
    assert verify_proof(manifest, tampered_checkpoint) is False
