"""Run against local Observer nodes to test conflict preservation and replica recovery."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import httpx

from oin.capture.http_capture import CaptureResult, build_wacz, build_warc
from oin.identity.keys import load_private_key
from oin.observation.service import build_observation
from oin.protocol.core import utc_now
from oin.timestamp.rfc3161 import local_declaration


def synthetic_capture() -> CaptureResult:
    url = "https://example.com/"
    body = b"<html><body><h1>Observer B divergent capture</h1></body></html>"
    headers = {"content-type": "text/html; charset=utf-8", "x-oin-test": "divergent"}
    captured_at = utc_now()
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, build_wacz(warc, url, captured_at))


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: e2e_conflict.py <observer-b-url> <observer-c-url> <observer-b-private-key>")
    b_url, c_url, key_path = sys.argv[1:]
    manifest, archive = build_observation(synthetic_capture(), load_private_key(Path(key_path)), archive_format="wacz")
    envelope = {
        "manifest": manifest,
        "archive_b64": base64.b64encode(archive).decode("ascii"),
        "source_node": "observer-b-local-test",
        "timestamp_evidence": local_declaration(manifest),
    }
    with httpx.Client(timeout=45.0) as client:
        imported = client.post(f"{b_url.rstrip('/')}/v1/observations", json=envelope).raise_for_status().json()
        object_id = manifest["object"]["object_id"]
        conflicts_b = client.get(f"{b_url.rstrip('/')}/v1/objects/{object_id}/conflicts").raise_for_status().json()
        pull_c = client.post(f"{c_url.rstrip('/')}/v1/replication/pull", json={"peer_url": b_url}).raise_for_status().json()
        observations_c = client.get(f"{c_url.rstrip('/')}/v1/objects/{object_id}/observations").raise_for_status().json()
    print(json.dumps({
        "divergent_observation_id": manifest["observation_id"],
        "object_id": object_id,
        "observer_b_import": imported,
        "observer_b_conflicts": conflicts_b,
        "observer_c_pull": pull_c,
        "observer_c_observation_count": len(observations_c),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
