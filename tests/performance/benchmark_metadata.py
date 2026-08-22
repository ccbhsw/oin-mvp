"""Deterministic local metadata benchmark; it does not claim network or storage-provider throughput."""

from __future__ import annotations

import argparse
import json
import resource
import tempfile
import time
try:
    try:
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
except ImportError:
    import datetime as dt
    UTC = dt.timezone.utc, datetime, timedelta
from pathlib import Path

from oin.api.repository import Repository
from oin.capture.http_capture import CaptureResult, build_wacz, build_warc
from oin.identity.keys import generate_keypair
from oin.observation.service import build_observation


def fixture_capture(captured_at: str) -> CaptureResult:
    url = "https://example.org/performance-object"
    headers = {"content-type": "text/html"}
    body = b"<html>OIN performance fixture</html>"
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, build_wacz(warc, url, captured_at))


def run_case(size: int, root: Path) -> dict[str, float | int]:
    database = root / f"observations-{size}.db"
    repo = Repository(f"sqlite:///{database}")
    repo.create_schema()
    key, _ = generate_keypair()
    start = datetime(2026, 8, 21, tzinfo=UTC)
    started = time.perf_counter()
    object_identifier = ""
    for index in range(size):
        captured_at = (start + timedelta(seconds=index)).isoformat().replace("+00:00", "Z")
        manifest, _ = build_observation(fixture_capture(captured_at), key)
        repo.save_observation(manifest, storage_backend="benchmark", storage_locator=f"benchmark/{index}")
        object_identifier = manifest["object"]["object_id"]
    ingest_seconds = time.perf_counter() - started

    query_started = time.perf_counter()
    observations = repo.observations_for_object(object_identifier)
    query_seconds = time.perf_counter() - query_started
    ids_started = time.perf_counter()
    ids = repo.list_observation_ids()
    ids_seconds = time.perf_counter() - ids_started
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "observation_records": size,
        "ingest_seconds": round(ingest_seconds, 6),
        "ingest_per_second": round(size / ingest_seconds, 3),
        "query_seconds": round(query_seconds, 6),
        "query_result_count": len(observations),
        "replication_id_listing_seconds": round(ids_seconds, 6),
        "replication_id_count": len(ids),
        "database_bytes": database.stat().st_size,
        "max_rss_kib": usage.ru_maxrss,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="100,1000,10000,100000")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sizes = [int(value) for value in args.sizes.split(",")]
    with tempfile.TemporaryDirectory(prefix="oin-performance-") as directory:
        results = [run_case(size, Path(directory)) for size in sizes]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"scope": "local SQLite metadata benchmark", "results": results}, indent=2) + "\n")
    print(args.output)


if __name__ == "__main__":
    main()
