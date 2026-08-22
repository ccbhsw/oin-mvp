#!/usr/bin/env python3
"""Experimental operator A. Uses Python stdlib plus cryptography only."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parent
OPERATOR_ID = "experimental-operator-a"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> bytes:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.write_bytes(raw)
    return raw


def load_or_create_key(keys: Path) -> tuple[Ed25519PrivateKey, bytes]:
    private_path = keys / "ed25519-private.pem"
    public_path = keys / "ed25519-public.pem"
    if private_path.exists():
        private = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
        assert isinstance(private, Ed25519PrivateKey)
    else:
        private = Ed25519PrivateKey.generate()
        private_path.write_bytes(private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_path.write_bytes(public)
    return private, public


def actual_get(url: str, headers: dict[str, str]) -> tuple[int, str, list[tuple[str, str]], bytes, str | None]:
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=30) as response:
            status = response.status
            reason = response.reason or ""
            response_headers = list(response.headers.items())
            body = response.read()
            return status, str(reason), response_headers, body, None
    except HTTPError as err:
        return err.code, str(err.reason or ""), list(err.headers.items()), err.read(), None
    except URLError as err:
        return 0, "TRANSPORT_ERROR", [], str(err).encode("utf-8"), str(err)


def http_message(status: int, reason: str, headers: list[tuple[str, str]], body: bytes) -> bytes:
    status_line = f"HTTP/1.1 {status} {reason}".rstrip() + "\r\n"
    cleaned = [(k, v) for k, v in headers if k.lower() not in {"content-length", "transfer-encoding"}]
    hlines = "".join(f"{k}: {v}\r\n" for k, v in cleaned)
    return (status_line + hlines + f"Content-Length: {len(body)}\r\n\r\n").encode("latin-1", "replace") + body


def warc_record(record_type: str, target: str, content_type: str, content: bytes, when: str, extra: dict[str, str]) -> bytes:
    fields = [
        "WARC/1.1",
        f"WARC-Type: {record_type}",
        f"WARC-Target-URI: {target}",
        f"WARC-Date: {when}",
        f"WARC-Record-ID: <urn:uuid:{uuid.uuid4()}>",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(content)}",
    ] + [f"{k}: {v}" for k, v in extra.items()]
    return ("\r\n".join(fields) + "\r\n\r\n").encode("utf-8") + content + b"\r\n\r\n"


def write_warc(out: Path, target: dict[str, object], headers: dict[str, str], status: int, reason: str,
               response_headers: list[tuple[str, str]], body: bytes, when: str) -> tuple[str, str]:
    request_text = (f"GET {target['url']} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n").encode()
    response = http_message(status, reason, response_headers, body)
    request_record = warc_record("request", str(target["url"]), "application/http; msgtype=request", request_text, when, {})
    response_record = warc_record("response", str(target["url"]), "application/http; msgtype=response", response, when, {
        "WARC-Payload-Digest": f"sha256:{sha256(body)}",
        "WARC-Concurrent-To": "<urn:uuid:request-record-not-stable>",
    })
    out.write_bytes(request_record + response_record)
    return sha256(out.read_bytes()), sha256(body)


def create_package(bundle_dir: Path, target: dict[str, object], capture: dict[str, object], warc: Path) -> Path:
    package_root = bundle_dir / "package-build"
    shutil.rmtree(package_root, ignore_errors=True)
    (package_root / "archive").mkdir(parents=True)
    (package_root / "indexes").mkdir(parents=True)
    shutil.copy2(warc, package_root / "archive" / "capture.warc")
    cdxj = {
        "url": target["url"],
        "timestamp": capture["captured_at"],
        "status": capture["status"],
        "digest": capture["payload_sha256"],
        "filename": "archive/capture.warc",
    }
    (package_root / "indexes" / "index.cdxj").write_text(f"{target['url']} {capture['captured_at'].replace('-', '').replace(':', '').replace('T', '').replace('Z', '')} {json.dumps(cdxj, sort_keys=True)}\n")
    metadata = {
        "format": "experimental-wacz-data-package",
        "capture": capture,
        "target": target["url"],
    }
    write_json(package_root / "metadata.json", metadata)
    resources = []
    for rel in ["archive/capture.warc", "indexes/index.cdxj", "metadata.json"]:
        raw = (package_root / rel).read_bytes()
        resources.append({"path": rel, "bytes": len(raw), "hash": f"sha256:{sha256(raw)}"})
    write_json(package_root / "datapackage.json", {"profile": "data-package", "resources": resources})
    package = bundle_dir / "evidence.wacz"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel in ["datapackage.json", "metadata.json", "archive/capture.warc", "indexes/index.cdxj"]:
            zf.write(package_root / rel, rel)
    shutil.rmtree(package_root)
    return package


def capture_one(op_root: Path, private: Ed25519PrivateKey, public_pem: bytes, target: dict[str, object]) -> dict[str, object]:
    headers = dict(target["request_headers"])
    headers["User-Agent"] = "MissionNetworkOperatorA/1.0"
    when = iso_now()
    status, reason, response_headers, body, transport_error = actual_get(str(target["url"]), headers)
    seed = f"{target['case_id']}:{when}:{sha256(body)}".encode()
    statement_id = sha256(seed)[:24]
    bundle = op_root / "bundles" / statement_id
    bundle.mkdir(parents=True)
    warc = bundle / "capture.warc"
    warc_sha256, payload_sha256 = write_warc(warc, target, headers, status, reason, response_headers, body, when)
    capture = {
        "captured_at": when,
        "status": status,
        "reason": reason,
        "request_headers": headers,
        "response_headers": response_headers,
        "payload_sha256": payload_sha256,
        "warc_sha256": warc_sha256,
        "transport_error": transport_error,
    }
    package = create_package(bundle, target, capture, warc)
    package_sha256 = sha256(package.read_bytes())
    statement = {
        "@context": ["https://www.w3.org/ns/credentials/v2", "https://www.w3.org/ns/prov#"],
        "type": ["VerifiableCredential", "CaptureEvidenceStatement"],
        "id": f"urn:sha256:{statement_id}",
        "issuer": {"id": OPERATOR_ID, "publicKeySha256": sha256(public_pem)},
        "validFrom": when,
        "credentialSubject": {
            "id": str(target["url"]),
            "capture": {
                "activity": "http-get",
                "requestHeaders": headers,
                "responseStatus": status,
                "responsePayloadSha256": payload_sha256,
                "transportError": transport_error,
            },
            "evidence": {
                "format": "WARC-1.1-in-WACZ-ZIP",
                "file": "evidence.wacz",
                "sha256": package_sha256,
                "warcSha256": warc_sha256,
                "location": f"/bundles/{statement_id}/",
            },
        },
    }
    statement_bytes = write_json(bundle / "statement.json", statement)
    (bundle / "statement.sig").write_bytes(private.sign(statement_bytes))
    (bundle / "signer-public.pem").write_bytes(public_pem)
    (bundle / "capture.warc").unlink()
    return {
        "statement_id": statement_id,
        "kind": "local-capture",
        "target": target["url"],
        "case_id": target["case_id"],
        "issuer": OPERATOR_ID,
        "captured_at": when,
        "bundle": f"/bundles/{statement_id}/",
        "statement_sha256": sha256(statement_bytes),
        "evidence_sha256": package_sha256,
        "payload_sha256": payload_sha256,
        "status": status,
        "public_key_sha256": sha256(public_pem),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", default=str(ROOT / "targets.json"))
    parser.add_argument("--operator-root", default=str(ROOT / "operators" / "operator-a"))
    parser.add_argument("--cases", nargs="+", default=["T01-unchanged", "T02-changed", "T03-redirect", "T04-canonical", "T05-language-header-variation", "T06-query-variation-alpha"])
    args = parser.parse_args()
    root = Path(args.operator_root)
    (root / "keys").mkdir(parents=True, exist_ok=True)
    private, public = load_or_create_key(root / "keys")
    data = json.loads(Path(args.targets).read_text())
    selected = [x for x in data["targets"] if x["case_id"] in set(args.cases)]
    entries = [capture_one(root, private, public, target) for target in selected]
    catalog = {
        "catalog_type": "signed-static-web-capture-catalog",
        "operator": {"id": OPERATOR_ID, "publicKeySha256": sha256(public)},
        "generated_at": iso_now(),
        "scope": {"kind": "local-and-explicit-imports", "completeness": "complete-for-this-directory-at-generation"},
        "entries": entries,
    }
    catalog_bytes = write_json(root / "catalog.json", catalog)
    (root / "catalog.sig").write_bytes(private.sign(catalog_bytes))
    (root / "catalog-public.pem").write_bytes(public)
    print(json.dumps({"operator": OPERATOR_ID, "entries": len(entries), "catalog_sha256": sha256(catalog_bytes)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
