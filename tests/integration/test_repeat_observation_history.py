from __future__ import annotations

from pathlib import Path

from oin.api.repository import Repository
from oin.capture.http_capture import CaptureResult, build_wacz, build_warc
from oin.identity.keys import generate_keypair
from oin.observation.service import build_observation


def capture(captured_at: str) -> CaptureResult:
    url = "https://example.org/repeated-content"
    headers = {"content-type": "text/html"}
    body = b"<html>unchanged page</html>"
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, build_wacz(warc, url, captured_at))


def test_same_observer_can_record_same_content_at_different_times(tmp_path: Path) -> None:
    repo = Repository(f"sqlite:///{tmp_path / 'history.db'}")
    repo.create_schema()
    key, _ = generate_keypair()
    first, _ = build_observation(capture("2026-08-21T10:00:00Z"), key)
    second, _ = build_observation(capture("2026-08-21T10:10:00Z"), key)

    repo.save_observation(first, storage_backend="test", storage_locator="first")
    repo.save_observation(second, storage_backend="test", storage_locator="second")

    history = repo.observations_for_object(first["object"]["object_id"])
    assert [item.observation_id for item in history] == [first["observation_id"], second["observation_id"]]
    assert history[0].raw_content_hash == history[1].raw_content_hash
