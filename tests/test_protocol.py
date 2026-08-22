from __future__ import annotations

from pathlib import Path

from oin.api.repository import Repository
from oin.capture.http_capture import CaptureResult
from oin.identity.keys import generate_keypair
from oin.observation.service import build_observation, export_bundle, verify_manifest
from oin.transparency.merkle import MerkleLog, verify_proof
from oin.verifier.offline import verify_bundle


def synthetic_capture(body: bytes, captured_at: str = "2026-08-21T10:00:00Z") -> CaptureResult:
    from oin.capture.http_capture import build_wacz, build_warc
    url = "https://example.org/policy?utm_source=ignored"
    headers = {"content-type": "text/html; charset=utf-8"}
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, build_wacz(warc, url, captured_at))


def test_signed_manifest_and_offline_bundle(tmp_path: Path) -> None:
    key, _ = generate_keypair()
    manifest, archive = build_observation(synthetic_capture(b"<html>A</html>"), key)
    assert verify_manifest(manifest)["valid"]
    export_bundle(tmp_path, manifest, archive)
    result = verify_bundle(tmp_path)
    assert result["status"] == "VALID"
    assert result["checks"]["raw_content_hash"] is True
    assert result["checks"]["observer_signature"] is True


def test_observation_tamper_is_detected(tmp_path: Path) -> None:
    key, _ = generate_keypair()
    manifest, archive = build_observation(synthetic_capture(b"<html>A</html>"), key)
    export_bundle(tmp_path, manifest, archive + b"evil")
    assert verify_bundle(tmp_path)["status"] == "INVALID"


def test_log_inclusion_proof(tmp_path: Path) -> None:
    key, _ = generate_keypair()
    first, _ = build_observation(synthetic_capture(b"A", "2026-08-21T10:00:00Z"), key)
    second, _ = build_observation(synthetic_capture(b"B", "2026-08-21T10:00:01Z"), key)
    log = MerkleLog(tmp_path / "log")
    log.append(first)
    log.append(second)
    proof = log.proof(first["observation_id"])
    assert proof is not None
    assert verify_proof(first, proof)


def test_conflicting_observations_are_both_retained(tmp_path: Path) -> None:
    repo = Repository(f"sqlite:///{tmp_path / 'test.db'}")
    repo.create_schema()
    key_a, _ = generate_keypair()
    key_b, _ = generate_keypair()
    a, _ = build_observation(synthetic_capture(b"A", "2026-08-21T10:00:00Z"), key_a)
    b, _ = build_observation(synthetic_capture(b"B", "2026-08-21T10:00:04Z"), key_b)
    repo.save_observation(a, storage_backend="test", storage_locator="a")
    repo.save_observation(b, storage_backend="test", storage_locator="b")
    candidate = repo.observation(b["observation_id"])
    assert candidate is not None
    repo.record_conflicts(b["object"]["object_id"], candidate)
    retained = repo.observations_for_object(a["object"]["object_id"])
    conflicts = repo.conflicts_for_object(a["object"]["object_id"])
    assert {item.observation_id for item in retained} == {a["observation_id"], b["observation_id"]}
    assert len(conflicts) == 1
    assert conflicts[0].classification == "observation_divergence"
    assert conflicts[0].is_conflict_candidate is True
