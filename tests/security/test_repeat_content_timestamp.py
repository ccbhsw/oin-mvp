from __future__ import annotations

import base64
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from oin.capture.http_capture import CaptureResult, build_wacz, build_warc
from oin.identity.keys import generate_keypair
from oin.observation.service import build_observation
from oin.timestamp.rfc3161 import rfc3161_request


OPENSSL_CNF = """
[ req ]
default_bits = 2048
distinguished_name = req_dn
prompt = no
x509_extensions = v3_ca

[ req_dn ]
CN = OIN Test TSA CA

[ v3_ca ]
basicConstraints = critical,CA:TRUE
keyUsage = critical, keyCertSign, cRLSign

[ tsa_req ]
distinguished_name = tsa_dn
prompt = no

[ tsa_dn ]
CN = OIN Test TSA

[ tsa_cert ]
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, timeStamping

[ tsa ]
default_tsa = tsa_section

[ tsa_section ]
dir = {dir}
serial = {dir}/tsaserial
crypto_device = builtin
signer_cert = {dir}/tsa.crt
signer_key = {dir}/tsa.key
signer_digest = sha256
default_policy = 1.2.3.4.1
digests = sha256
accuracy = secs:1
ordering = yes
ess_cert_id_chain = no
"""


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(args)}\n{result.stderr or result.stdout}")
    return result


@pytest.fixture(scope="module")
def tsa_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("tsa")
    (root / "openssl.cnf").write_text(OPENSSL_CNF.format(dir=root))
    _run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650",
            "-keyout", str(root / "ca.key"), "-out", str(root / "ca.crt"),
            "-subj", "/CN=OIN Test TSA CA",
            "-config", str(root / "openssl.cnf"), "-extensions", "v3_ca",
        ]
    )
    _run(
        [
            "openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(root / "tsa.key"), "-out", str(root / "tsa.csr"),
            "-subj", "/CN=OIN Test TSA",
        ]
    )
    _run(
        [
            "openssl", "x509", "-req", "-in", str(root / "tsa.csr"),
            "-CA", str(root / "ca.crt"), "-CAkey", str(root / "ca.key"),
            "-CAcreateserial", "-out", str(root / "tsa.crt"), "-days", "3650",
            "-extfile", str(root / "openssl.cnf"), "-extensions", "tsa_cert",
        ]
    )
    (root / "tsaserial").write_text("01\n")
    return root


def issue_rfc3161_evidence(manifest: dict, tsa_dir: Path) -> dict:
    query = rfc3161_request(manifest)
    query_path = tsa_dir / "request.tsq"
    reply_path = tsa_dir / "reply.tsr"
    query_path.write_bytes(query)
    _run(
        [
            "openssl", "ts", "-reply",
            "-queryfile", str(query_path),
            "-inkey", str(tsa_dir / "tsa.key"),
            "-signer", str(tsa_dir / "tsa.crt"),
            "-config", str(tsa_dir / "openssl.cnf"),
            "-out", str(reply_path),
        ]
    )
    from oin.protocol.core import canonical_json, sha256_prefixed

    return {
        "kind": "rfc3161",
        "message_imprint": sha256_prefixed(canonical_json(manifest)),
        "tsa_url": "local-openssl-tsa",
        "token_der_b64": base64.b64encode(reply_path.read_bytes()).decode("ascii"),
        "tsa_ca_pem": (tsa_dir / "ca.crt").read_text(),
    }


def make_capture(url: str, body: bytes, captured_at: str) -> CaptureResult:
    headers = {"content-type": "text/html"}
    warc = build_warc(url, captured_at, 200, headers, body)
    return CaptureResult(url, url, captured_at, 200, headers, [url], body, "text/html", warc, build_wacz(warc, url, captured_at))


def envelope(manifest: dict, archive: bytes, timestamp_evidence: dict | None = None) -> dict:
    payload = {
        "manifest": manifest,
        "archive_b64": base64.b64encode(archive).decode("ascii"),
        "source_node": "test",
    }
    if timestamp_evidence is not None:
        payload["timestamp_evidence"] = timestamp_evidence
    return payload


def test_repeat_content_requires_rfc3161_on_second_submit(tsa_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OIN_PUBLIC_LOCKDOWN", raising=False)
    from oin.api.app import app

    client = TestClient(app)
    token = uuid.uuid4().hex
    url = f"https://example.org/repeat-ts-{token}"
    body = f"<html>repeat-ts-{token}</html>".encode()
    key, _ = generate_keypair()

    first_manifest, first_archive = build_observation(make_capture(url, body, "2026-08-21T10:00:00Z"), key)
    first = client.post("/v1/observations", json=envelope(first_manifest, first_archive))
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "created"

    second_manifest, second_archive = build_observation(make_capture(url, body, "2026-08-21T11:00:00Z"), key)
    assert second_manifest["content"]["raw_content_hash"] == first_manifest["content"]["raw_content_hash"]
    assert second_manifest["capture"]["captured_at"] != first_manifest["capture"]["captured_at"]
    assert second_manifest["observation_id"] != first_manifest["observation_id"]

    denied = client.post("/v1/observations", json=envelope(second_manifest, second_archive))
    assert denied.status_code == 422, denied.text
    detail = denied.json()["detail"]
    assert detail["reason"] == "TIMESTAMP_EVIDENCE_REQUIRED"
    assert "重复内容再次提交必须提供第三方时间戳" in detail["detail"]

    evidence = issue_rfc3161_evidence(second_manifest, tsa_dir)
    accepted = client.post(
        "/v1/observations",
        json=envelope(second_manifest, second_archive, evidence),
    )
    assert accepted.status_code == 201, accepted.text
    observation_id = second_manifest["observation_id"]
    verified = client.get(f"/v1/verify/{observation_id}")
    assert verified.status_code == 200, verified.text
    payload = verified.json()
    assert payload["status"] == "VALID"
    timestamp = payload["timestamp"]
    assert timestamp["kind"] == "rfc3161"
    assert timestamp["kind"] != "local-declaration"
    assert timestamp["captured_at"] == "2026-08-21T11:00:00Z"
    assert timestamp["tsa_time"]
    assert timestamp["captured_at_vs_tsa"] is not None
    assert "delta_seconds" in timestamp["captured_at_vs_tsa"]
    assert timestamp["captured_at_vs_tsa"]["note"]
