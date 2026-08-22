"""Export an OIN verification bundle from a node without relying on its website afterward."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import httpx


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: export_bundle_from_node.py <node-url> <observation-id> <output-dir>")
    node, observation_id, output = sys.argv[1:]
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=45.0) as client:
        payload = client.get(f"{node.rstrip('/')}/v1/replication/export/{observation_id}").raise_for_status().json()
    manifest = payload["manifest"]
    archive = base64.b64decode(payload["archive_b64"], validate=True)
    extension = manifest["content"]["archive_format"]
    (output_path / "observation.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (output_path / f"raw.{extension}").write_bytes(archive)
    (output_path / "observer-public.json").write_text(json.dumps(manifest["observer"], indent=2, sort_keys=True) + "\n")
    evidence = {
        "timestamp": payload.get("timestamp_evidence"),
        "transparency_proof": payload.get("source_proof"),
    }
    (output_path / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output_path), "observation_id": observation_id, "archive": f"raw.{extension}"}))


if __name__ == "__main__":
    main()
