#!/usr/bin/env python3
"""Verifier and multi-peer discovery client for signed WARC/WACZ evidence bundles."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import re
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read()


def verify_signature(public_pem: bytes, payload: bytes, signature: bytes) -> bool:
    try:
        serialization.load_pem_public_key(public_pem).verify(signature, payload)
        return True
    except (ValueError, InvalidSignature):
        return False


def url_join(base: str, relative: str) -> str:
    return base.rstrip("/") + "/" + relative.lstrip("/")


def verify_package(raw: bytes) -> tuple[bool, list[str], dict[str, str]]:
    problems: list[str] = []
    details: dict[str, str] = {}
    from io import BytesIO
    try:
        with zipfile.ZipFile(BytesIO(raw)) as zf:
            bad = zf.testzip()
            if bad:
                problems.append(f"zip_crc_failure:{bad}")
            manifest = json.loads(zf.read("datapackage.json"))
            for resource in manifest.get("resources", []):
                path = resource["path"]
                expected = resource["hash"].removeprefix("sha256:")
                actual = sha256(zf.read(path))
                if actual != expected:
                    problems.append(f"resource_digest_mismatch:{path}")
            warc = zf.read("archive/capture.warc")
            details["warc_sha256"] = sha256(warc)
            match = re.search(br"WARC-Payload-Digest: sha256:([0-9a-f]{64})", warc)
            if not match:
                problems.append("warc_payload_digest_missing")
            else:
                details["warc_payload_sha256"] = match.group(1).decode()
    except Exception as exc:
        problems.append(f"package_error:{type(exc).__name__}:{exc}")
    return not problems, problems, details


def verify_catalog(peer: dict[str, str]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    base = peer["base_url"]
    try:
        raw = fetch(url_join(base, "catalog.json"))
        signature = fetch(url_join(base, "catalog.sig"))
        public = fetch(url_join(base, "catalog-public.pem"))
    except Exception as exc:
        return None, {"peer": peer["operator"], "catalog_valid": False, "error": f"fetch:{type(exc).__name__}"}
    valid = verify_signature(public, raw, signature)
    try:
        catalog = json.loads(raw)
    except Exception as exc:
        return None, {"peer": peer["operator"], "catalog_valid": False, "error": f"json:{type(exc).__name__}"}
    public_match = catalog.get("operator", {}).get("publicKeySha256") == sha256(public)
    if not valid or not public_match:
        return None, {"peer": peer["operator"], "catalog_valid": False, "error": "signature_or_public_key_mismatch"}
    return catalog, {"peer": peer["operator"], "catalog_valid": True, "entries": len(catalog.get("entries", []))}


def verify_entry(base: str, entry: dict[str, Any]) -> dict[str, Any]:
    relative = entry["bundle"]
    result: dict[str, Any] = {"statement_id": entry["statement_id"], "issuer": entry["issuer"], "target": entry["target"], "bundle": relative}
    try:
        statement_raw = fetch(url_join(base, relative + "statement.json"))
        sig = fetch(url_join(base, relative + "statement.sig"))
        public = fetch(url_join(base, relative + "signer-public.pem"))
        package = fetch(url_join(base, relative + "evidence.wacz"))
    except Exception as exc:
        result.update({"valid": False, "error": f"bundle_fetch:{type(exc).__name__}"})
        return result
    signature_valid = verify_signature(public, statement_raw, sig)
    try:
        statement = json.loads(statement_raw)
    except Exception as exc:
        result.update({"valid": False, "error": f"statement_json:{type(exc).__name__}"})
        return result
    subject = statement.get("credentialSubject", {})
    evidence = subject.get("evidence", {})
    package_valid, problems, package_details = verify_package(package)
    binding_ok = (
        statement.get("issuer", {}).get("id") == entry["issuer"]
        and statement.get("issuer", {}).get("publicKeySha256") == sha256(public)
        and statement.get("id") == f"urn:sha256:{entry['statement_id']}"
        and entry.get("statement_sha256") == sha256(statement_raw)
        and evidence.get("sha256") == sha256(package)
        and entry.get("evidence_sha256") == sha256(package)
        and evidence.get("warcSha256") == package_details.get("warc_sha256")
        and subject.get("capture", {}).get("responsePayloadSha256") == package_details.get("warc_payload_sha256")
        and subject.get("id") == entry["target"]
    )
    result.update({
        "valid": signature_valid and binding_ok and package_valid,
        "signature_valid": signature_valid,
        "binding_valid": binding_ok,
        "package_valid": package_valid,
        "package_problems": problems,
        "statement_sha256": sha256(statement_raw),
        "evidence_sha256": sha256(package),
        "captured_at": entry.get("captured_at"),
        "status": entry.get("status"),
        "payload_sha256": entry.get("payload_sha256"),
        "claim_key": subject.get("capture", {}).get("claimKey"),
        "warc_sha256": package_details.get("warc_sha256"),
    })
    return result


def discover(peers: list[dict[str, str]], target: str) -> dict[str, Any]:
    report: dict[str, Any] = {"target": target, "peer_reports": [], "matches": []}
    for peer in peers:
        catalog, state = verify_catalog(peer)
        report["peer_reports"].append(state)
        if catalog is None:
            continue
        for entry in catalog.get("entries", []):
            if entry.get("target") == target:
                verified = verify_entry(peer["base_url"], entry)
                verified["peer"] = peer["operator"]
                report["matches"].append(verified)
    report["valid_match_count"] = sum(1 for x in report["matches"] if x.get("valid"))
    report["distinct_payloads"] = sorted({x.get("payload_sha256") for x in report["matches"] if x.get("valid")})
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for match in report["matches"]:
        if match.get("valid") and match.get("claim_key"):
            groups.setdefault((match["issuer"], match["target"], match["claim_key"]), []).append(match)
    report["same_signer_conflicts"] = [
        {"issuer": key[0], "target": key[1], "claim_key": key[2], "statement_ids": sorted({item["statement_id"] for item in values}), "distinct_payloads": sorted({item["payload_sha256"] for item in values})}
        for key, values in groups.items() if len({item["payload_sha256"] for item in values}) > 1
    ]
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--peers", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    peers_doc = json.loads(Path(args.peers).read_text())
    report = discover(peers_doc["peers"], args.target)
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"target": args.target, "valid_match_count": report["valid_match_count"], "peer_reports": len(report["peer_reports"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
