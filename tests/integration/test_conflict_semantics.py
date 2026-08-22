from __future__ import annotations

from pathlib import Path

from oin.api.repository import Repository
from oin.capture.http_capture import CaptureResult, build_wacz, build_warc
from oin.identity.keys import generate_keypair
from oin.observation.service import build_observation


def synthetic_capture(body: bytes, captured_at: str) -> CaptureResult:
    url = "https://example.org/stage2-object"
    headers = {"content-type": "text/html; charset=utf-8"}
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, build_wacz(warc, url, captured_at))


def test_temporal_variation_is_not_a_conflict_and_history_is_retained(tmp_path: Path) -> None:
    repo = Repository(f"sqlite:///{tmp_path / 'temporal.db'}")
    repo.create_schema()
    key_a, _ = generate_keypair()
    key_b, _ = generate_keypair()
    first, _ = build_observation(synthetic_capture(b"<html>first</html>", "2026-08-21T10:00:00Z"), key_a)
    later, _ = build_observation(synthetic_capture(b"<html>later</html>", "2026-08-21T10:10:01Z"), key_b)

    repo.save_observation(first, storage_backend="test", storage_locator="first")
    repo.save_observation(later, storage_backend="test", storage_locator="later")
    stored = repo.observation(later["observation_id"])
    assert stored is not None
    created = repo.record_conflicts(later["object"]["object_id"], stored)

    history = repo.observations_for_object(first["object"]["object_id"])
    assert {entry.observation_id for entry in history} == {first["observation_id"], later["observation_id"]}
    assert len(created) == 1
    assert created[0].classification == "temporal_variation"
    assert created[0].is_conflict_candidate is False
