#!/usr/bin/env python3
"""Generate a deterministic, offline IWOH v0.1 interoperability corpus.

This generator is corpus construction tooling only.  Independent verifiers must
not import it or share code with it.  It does not read the OIN MVP.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path("/home/ubuntu/oin-candidate-validation/fixtures")
CONTEXT = ["https://www.w3.org/ns/credentials/v2", "https://example.test/iwhoh/v1"]
ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
FIXTURE_CREATED = "2026-08-21T00:00:00Z"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(data: bytes) -> str:
    return "sha256:" + sha256(data)


def b58encode(data: bytes) -> str:
    value = int.from_bytes(data, "big")
    encoded = bytearray()
    while value:
        value, remainder = divmod(value, 58)
        encoded.append(ALPHABET[remainder])
    leading = len(data) - len(data.lstrip(b"\0"))
    return (ALPHABET[:1] * leading + encoded[::-1]).decode("ascii")


def canonical_json(value: Any) -> bytes:
    # Inputs contain only I-JSON-compatible strings, booleans, integers, arrays
    # and objects, so Python's deterministic JSON serialization matches JCS here.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class FixtureSigner:
    def __init__(self) -> None:
        labels = [
            "observer-a", "observer-b", "observer-c", "sequence-primary",
            "sequence-parallel-a", "sequence-parallel-b", "history-archive",
            "transparency-log",
        ]
        self.identities: dict[str, dict[str, Any]] = {}
        for label in labels:
            seed = hashlib.sha256(("IWOH-v0.1-fixture:" + label).encode("ascii")).digest()
            private = Ed25519PrivateKey.from_private_bytes(seed)
            public = private.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            issuer = f"https://{label}.example.test"
            vm = issuer + "#key-1"
            self.identities[label] = {
                "private": private,
                "issuer": issuer,
                "verification_method": vm,
                # Multikey Ed25519 multicodec prefix is 0xed01.
                "publicKeyMultibase": "z" + b58encode(b"\xed\x01" + public),
            }

    def registry(self) -> dict[str, Any]:
        items = []
        for label, identity in self.identities.items():
            items.append({
                "id": identity["verification_method"],
                "controller": identity["issuer"],
                "type": "Multikey",
                "publicKeyMultibase": identity["publicKeyMultibase"],
                "purposes": ["assertionMethod"],
                "fixture_label": label,
            })
        return {"profile_version": "IWOH-0.1", "verification_methods": items}

    def sign(self, unsecured: dict[str, Any], label: str) -> dict[str, Any]:
        identity = self.identities[label]
        proof = {
            "type": "DataIntegrityProof",
            "cryptosuite": "eddsa-jcs-2022",
            "created": FIXTURE_CREATED,
            "verificationMethod": identity["verification_method"],
            "proofPurpose": "assertionMethod",
            "@context": unsecured["@context"],
        }
        hash_data = hashlib.sha256(canonical_json(proof)).digest() + hashlib.sha256(canonical_json(unsecured)).digest()
        signature = identity["private"].sign(hash_data)
        proof["proofValue"] = "z" + b58encode(signature)
        signed = copy.deepcopy(unsecured)
        signed["proof"] = proof
        return signed


SIGNER = FixtureSigner()


def safe_id(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "https://fixture.example.test/" + name))


def fixed_zip_write(zip_file: zipfile.ZipFile, name: str, content: bytes, compression: int) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 8, 21, 0, 0, 0))
    info.compress_type = compression
    info.external_attr = 0o644 << 16
    zip_file.writestr(info, content)


def make_warc_record(record_id: str, target: str, stamp: str, status: int, headers: dict[str, str], payload: bytes) -> bytes:
    reason = "Found" if status == 302 else "OK"
    response_headers = {"Content-Length": str(len(payload)), **headers}
    http = (f"HTTP/1.1 {status} {reason}\r\n" + "".join(f"{k}: {v}\r\n" for k, v in response_headers.items()) + "\r\n").encode("utf-8") + payload
    block_digest = digest(http)
    warc_header = (
        "WARC/1.1\r\n"
        "WARC-Type: response\r\n"
        f"WARC-Record-ID: <{record_id}>\r\n"
        f"WARC-Date: {stamp}\r\n"
        f"WARC-Target-URI: {target}\r\n"
        "Content-Type: application/http; msgtype=response\r\n"
        f"Content-Length: {len(http)}\r\n"
        f"WARC-Block-Digest: {block_digest}\r\n"
        "\r\n"
    ).encode("utf-8")
    return warc_header + http + b"\r\n\r\n"


def make_wacz(name: str, target: str, stamp: str, status: int, headers: dict[str, str], payload: bytes, tamper: bool = False) -> dict[str, Any]:
    record_id = "urn:uuid:" + safe_id("record:" + name)
    original_warc = make_warc_record(record_id, target, stamp, status, headers, payload)
    warc_for_zip = original_warc
    if tamper:
        marker = b"fixture-body-original"
        if marker not in warc_for_zip:
            raise ValueError("tamper marker absent")
        warc_for_zip = warc_for_zip.replace(marker, b"fixture-body-altered-", 1)
    pages = (
        '{"format":"json-pages-1.0","id":"pages","title":"IWOH Fixtures"}\n'
        + json.dumps({"id": name, "url": target, "ts": stamp, "title": name}, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    index = (
        target.replace("://", "://").replace("/", ")")
        + " " + stamp.replace("-", "").replace(":", "").replace("T", "").replace("Z", "")[:14]
        + " {\"url\":\"" + target + "\",\"filename\":\"data.warc\",\"record_id\":\"" + record_id + "\"}\n"
    ).encode("utf-8")
    resources_original = {
        "archive/data.warc": original_warc,
        "indexes/index.cdxj": index,
        "pages/pages.jsonl": pages,
    }
    manifest = {
        "profile": "data-package",
        "wacz_version": "1.1.1",
        "title": "IWOH v0.1 interoperability fixture " + name,
        "description": "Synthetic offline evidence only.",
        "created": FIXTURE_CREATED,
        "mainPageUrl": target,
        "mainPageDate": stamp,
        "resources": [
            {"name": path.rsplit("/", 1)[-1], "path": path, "hash": digest(content), "bytes": len(content)}
            for path, content in resources_original.items()
        ],
    }
    manifest_bytes = canonical_json(manifest)
    package_digest = canonical_json({"path": "datapackage.json", "hash": digest(manifest_bytes)})
    output = ROOT / "artifacts" / f"{name}.wacz"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", allowZip64=False) as archive:
        fixed_zip_write(archive, "archive/data.warc", warc_for_zip, zipfile.ZIP_STORED)
        fixed_zip_write(archive, "indexes/index.cdxj", index, zipfile.ZIP_STORED)
        fixed_zip_write(archive, "pages/pages.jsonl", pages, zipfile.ZIP_DEFLATED)
        fixed_zip_write(archive, "datapackage.json", manifest_bytes, zipfile.ZIP_DEFLATED)
        fixed_zip_write(archive, "datapackage-digest.json", package_digest, zipfile.ZIP_DEFLATED)
    return {
        "path": f"artifacts/{name}.wacz",
        "record_id": record_id,
        "wacz_digest": digest(output.read_bytes()),
        "payload_digest": digest(payload),
        "payload_length": len(payload),
    }


def defaults() -> tuple[dict[str, Any], dict[str, str]]:
    context = {
        "method": "GET",
        "recorded_request_headers": {"accept-language": "en"},
        "authentication_class": "ANONYMOUS",
        "network_vantage": {"id": "vantage-1", "vantage_effect": "NONE_EXPECTED"},
        "capture_policy": {
            "redirect_handling": "record-final-and-chain",
            "cookie_policy": "none",
            "content_decoding": "identity",
            "capture_scope": "response-only",
        },
    }
    return context, {"Content-Type": "text/plain; charset=utf-8"}


def make_statement(
    sid: str,
    artifact: dict[str, Any],
    target: str,
    stamp: str,
    *,
    issuer_label: str = "observer-a",
    signer_label: str | None = None,
    request_context: dict[str, Any] | None = None,
    response_headers: dict[str, str] | None = None,
    status: int = 200,
    time_evidence: dict[str, Any] | None = None,
    relations: list[dict[str, str]] | None = None,
    raw_reference: str | None = None,
) -> dict[str, Any]:
    context, default_headers = defaults()
    if request_context:
        context.update(copy.deepcopy(request_context))
    headers = response_headers or default_headers
    issuer = SIGNER.identities[issuer_label]["issuer"]
    doc: dict[str, Any] = {
        "@context": CONTEXT,
        "id": f"https://statements.example.test/{sid}",
        "type": ["VerifiableCredential", "WebObservationCapture"],
        "profile_version": "IWOH-0.1",
        "issuer": issuer,
        "capture_activity": {
            "id": f"https://activities.example.test/{sid}",
            "type": "prov:Activity",
            "started_at": stamp,
            "ended_at": stamp,
            "method": "http-capture",
            "software": "fixture-capture/0.1",
        },
        "request_target": {
            "uri": target.split("#", 1)[0],
            "uri_normalization": "rfc3986-basic; fragment-removed",
            "identity_kind": "request-target",
        },
        "request_context": context,
        "response": {
            "status": status,
            "recorded_response_headers": headers,
            "payload_digest": artifact["payload_digest"],
            "body_byte_length": artifact["payload_length"],
        },
        "evidence": {
            "artifact": artifact["path"],
            "wacz_digest": artifact["wacz_digest"],
            "warc_record_id": artifact["record_id"],
            "payload_digest": artifact["payload_digest"],
        },
        "time_evidence": time_evidence or {
            "kind": "local-declaration",
            "interval": {"not_before": stamp, "not_after": stamp},
            "precision": "PT1S",
        },
        "capture_context_completeness": "COMPLETE_FOR_REPRESENTATION_SELECTION",
    }
    if raw_reference:
        doc["request_target"]["source_reference_uri"] = raw_reference
    if relations:
        doc["target_relations"] = relations
    signed = SIGNER.sign(doc, signer_label or issuer_label)
    write_json(ROOT / "statements" / f"{sid}.json", signed)
    return signed


def make_receipt(name: str, statement_id: str, signer_label: str, log_id: str, ordinal: int, before: str, after: str, predecessors: list[str]) -> str:
    doc = {
        "@context": CONTEXT,
        "id": f"https://receipts.example.test/{name}",
        "type": ["VerifiableCredential", "WebObservationSequenceReceipt"],
        "profile_version": "IWOH-0.1",
        "issuer": SIGNER.identities[signer_label]["issuer"],
        "statement_id": statement_id,
        "log_id": log_id,
        "ordinal": ordinal,
        "interval": {"not_before": before, "not_after": after},
        "predecessor_statement_ids": predecessors,
    }
    signed = SIGNER.sign(doc, signer_label)
    relative = f"receipts/{name}.json"
    write_json(ROOT / relative, signed)
    return relative


def causal_receipt(reference: str) -> dict[str, Any]:
    return {"kind": "causal-receipt", "receipt": reference, "precision": "PT1S"}


def make_history(name: str, signer_label: str, scope: str, completeness: str, members: list[str], *, checkpoint: dict[str, Any] | None = None) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "@context": CONTEXT,
        "id": f"https://history.example.test/{name}",
        "type": ["VerifiableCredential", "WebObservationHistoryView"],
        "profile_version": "IWOH-0.1",
        "issuer": SIGNER.identities[signer_label]["issuer"],
        "history_scope": scope,
        "coverage": {
            "target_relation_policy": "exact-request-target-only",
            "time_interval": {"from": "2026-01-01T00:00:00Z", "until": "2026-12-31T23:59:59Z"},
            "ingestion_policy": "signed-statements-only",
        },
        "completeness": completeness,
        "scope_evidence": f"fixture:{name}",
        "statement_ids": [f"https://statements.example.test/{member}" for member in members],
    }
    if checkpoint:
        doc["checkpoint"] = checkpoint
    signed = SIGNER.sign(doc, signer_label)
    write_json(ROOT / "history" / f"{name}.json", signed)
    return signed


def result(
    target_identity: str,
    target_relation: str,
    validity: dict[str, str],
    comparability: str,
    relationship: str,
    membership: str = "NOT_APPLICABLE",
    completeness: str = "NOT_APPLICABLE",
    import_validity: str = "NOT_APPLICABLE",
    equivocation: str = "NOT_APPLICABLE",
) -> dict[str, Any]:
    return {
        "target_identity": target_identity,
        "target_relation": target_relation,
        "statement_validity": validity,
        "comparability": comparability,
        "relationship": relationship,
        "history_membership": membership,
        "completeness_scope": completeness,
        "statement_import_validity": import_validity,
        "equivocation_status": equivocation,
    }


def build() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    for directory in ("keys", "artifacts", "statements", "receipts", "history"):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    write_json(ROOT / "keys" / "public_keys.json", SIGNER.registry())
    write_json(ROOT / "trust_registry.json", {
        "profile_version": "IWOH-0.1",
        "trusted_assertion_method_controllers": [x["issuer"] for x in SIGNER.identities.values()],
        "trusted_time_receipt_issuers": [
            SIGNER.identities[x]["issuer"] for x in ("sequence-primary", "sequence-parallel-a", "sequence-parallel-b")
        ],
        "trusted_history_issuers": [SIGNER.identities[x]["issuer"] for x in ("history-archive", "transparency-log")],
    })

    artifacts: dict[str, dict[str, Any]] = {}
    statements: dict[str, dict[str, Any]] = {}

    def capture(
        sid: str, target: str, body: str, stamp: str, *, status: int = 200, headers: dict[str, str] | None = None,
        tamper: bool = False, issuer: str = "observer-a", signer: str | None = None,
        context: dict[str, Any] | None = None, time: dict[str, Any] | None = None,
        relations: list[dict[str, str]] | None = None, raw_reference: str | None = None,
    ) -> dict[str, Any]:
        h = headers or {"Content-Type": "text/plain; charset=utf-8"}
        artifact = make_wacz(sid, target.split("#", 1)[0], stamp, status, h, body.encode("utf-8"), tamper)
        artifacts[sid] = artifact
        statements[sid] = make_statement(
            sid, artifact, target, stamp, issuer_label=issuer, signer_label=signer,
            request_context=context, response_headers=h, status=status, time_evidence=time,
            relations=relations, raw_reference=raw_reference,
        )
        return statements[sid]

    # Identity: fragments must not change the request target.
    capture("fragment-a", "https://site.example.test/page#section-a", "same-fragment-body", "2026-02-01T00:00:00Z", raw_reference="https://site.example.test/page#section-a")
    capture("fragment-b", "https://site.example.test/page#section-b", "same-fragment-body", "2026-02-01T00:01:00Z", raw_reference="https://site.example.test/page#section-b", issuer="observer-b")
    # Query strings are retained and not silently normalized away.
    capture("query-a", "https://site.example.test/search?q=one", "query-one", "2026-02-02T00:00:00Z")
    capture("query-b", "https://site.example.test/search?q=two", "query-two", "2026-02-02T00:01:00Z", issuer="observer-b")

    final_uri = "https://site.example.test/final"
    redirect_relation = [{"relation": "redirect-final-uri", "from": "https://short.example.test/r", "to": final_uri, "asserted_by": "response"}]
    capture("redirect-source", "https://short.example.test/r", "redirect-body", "2026-02-03T00:00:00Z", status=302, headers={"Location": final_uri, "Content-Type": "text/plain"}, relations=redirect_relation)
    capture("redirect-final", final_uri, "final-body", "2026-02-03T00:01:00Z", issuer="observer-b")

    canonical_uri = "https://site.example.test/canonical"
    canonical_relation = [{"relation": "html-canonical", "from": "https://site.example.test/alias", "to": canonical_uri, "asserted_by": "response"}]
    capture("canonical-alias", "https://site.example.test/alias", f'<html><link rel="canonical" href="{canonical_uri}"></html>', "2026-02-04T00:00:00Z", headers={"Content-Type": "text/html"}, relations=canonical_relation)
    capture("canonical-final", canonical_uri, "canonical-final-body", "2026-02-04T00:01:00Z", issuer="observer-b")

    language_en = {"recorded_request_headers": {"accept-language": "en"}}
    language_zh = {"recorded_request_headers": {"accept-language": "zh"}}
    vary_headers = {"Content-Type": "text/plain", "Vary": "Accept-Language"}
    capture("language-en", "https://site.example.test/greeting", "Hello", "2026-02-05T00:00:00Z", headers=vary_headers, context=language_en)
    capture("language-zh", "https://site.example.test/greeting", "Ni Hao", "2026-02-05T00:01:00Z", headers=vary_headers, context=language_zh, issuer="observer-b")

    vantage_a = {"network_vantage": {"id": "geo-us", "vantage_effect": "UNKNOWN"}}
    vantage_b = {"network_vantage": {"id": "geo-eu", "vantage_effect": "UNKNOWN"}}
    capture("vantage-us", "https://site.example.test/price", "USD 10", "2026-02-06T00:00:00Z", context=vantage_a)
    capture("vantage-eu", "https://site.example.test/price", "EUR 9", "2026-02-06T00:01:00Z", context=vantage_b, issuer="observer-b")

    auth_public = {"authentication_class": "ANONYMOUS"}
    auth_private = {"authentication_class": "AUTHENTICATED"}
    capture("auth-public", "https://site.example.test/profile", "public-profile", "2026-02-07T00:00:00Z", context=auth_public)
    capture("auth-private", "https://site.example.test/profile", "private-profile", "2026-02-07T00:01:00Z", context=auth_private, issuer="observer-b")

    capture("repeated-a", "https://site.example.test/stable", "stable-representation", "2026-02-08T00:00:00Z")
    capture("repeated-b", "https://site.example.test/stable", "stable-representation", "2026-02-08T01:00:00Z", issuer="observer-b")

    old_id = "https://statements.example.test/temporal-old"
    new_id = "https://statements.example.test/temporal-new"
    old_receipt = make_receipt("temporal-old", old_id, "sequence-primary", "sequence-primary-log", 1, "2026-02-09T00:00:00Z", "2026-02-09T00:00:01Z", [])
    new_receipt = make_receipt("temporal-new", new_id, "sequence-primary", "sequence-primary-log", 2, "2026-02-09T00:10:00Z", "2026-02-09T00:10:01Z", [old_id])
    capture("temporal-old", "https://site.example.test/changing", "version-one", "2026-02-09T00:00:00Z", time=causal_receipt(old_receipt))
    capture("temporal-new", "https://site.example.test/changing", "version-two", "2026-02-09T00:10:00Z", issuer="observer-b", time=causal_receipt(new_receipt))

    parallel_a_id = "https://statements.example.test/parallel-a"
    parallel_b_id = "https://statements.example.test/parallel-b"
    parallel_a_receipt = make_receipt("parallel-a", parallel_a_id, "sequence-parallel-a", "parallel-log-a", 7, "2026-02-10T00:00:00Z", "2026-02-10T00:05:00Z", [])
    parallel_b_receipt = make_receipt("parallel-b", parallel_b_id, "sequence-parallel-b", "parallel-log-b", 9, "2026-02-10T00:03:00Z", "2026-02-10T00:08:00Z", [])
    capture("parallel-a", "https://site.example.test/live", "observer-a-view", "2026-02-10T00:00:00Z", time=causal_receipt(parallel_a_receipt))
    capture("parallel-b", "https://site.example.test/live", "observer-b-view", "2026-02-10T00:03:00Z", issuer="observer-b", time=causal_receipt(parallel_b_receipt))

    capture("clock-skew-a", "https://site.example.test/skew", "clock-one", "2026-02-11T02:00:00Z")
    capture("clock-skew-b", "https://site.example.test/skew", "clock-two", "2026-02-11T01:00:00Z", issuer="observer-b")

    capture("tampered-wacz", "https://site.example.test/tampered", "fixture-body-original", "2026-02-12T00:00:00Z", tamper=True)
    capture("agent-binding-error", "https://site.example.test/agent", "agent-binding", "2026-02-13T00:00:00Z", issuer="observer-a", signer="observer-b")
    capture("missing-history-statement", "https://site.example.test/missing", "outside-complete-view", "2026-02-14T00:00:00Z")
    capture("partial-history-statement", "https://site.example.test/partial", "outside-partial-view", "2026-02-15T00:00:00Z")
    capture("imported-valid", "https://site.example.test/import", "importable-evidence", "2026-02-16T00:00:00Z", issuer="observer-c")

    make_history("complete-history", "transparency-log", "TRANSPARENCY_LOG", "COMPLETE_FOR_DECLARED_SCOPE", ["repeated-a", "repeated-b"], checkpoint={"log_id": "fixture-history-log", "tree_size": 12, "root_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111"})
    make_history("partial-history", "history-archive", "ARCHIVE_LOCAL", "PARTIAL", ["repeated-a"])
    equivocation_a = make_history("equivocation-left", "transparency-log", "TRANSPARENCY_LOG", "COMPLETE_FOR_DECLARED_SCOPE", ["repeated-a"], checkpoint={"log_id": "equivocation-log", "tree_size": 42, "root_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"})
    equivocation_b = make_history("equivocation-right", "transparency-log", "TRANSPARENCY_LOG", "COMPLETE_FOR_DECLARED_SCOPE", ["repeated-a"], checkpoint={"log_id": "equivocation-log", "tree_size": 42, "root_hash": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"})

    scenarios = [
        {"id": "fragment_identity", "kind": "comparison", "statements": ["fragment-a", "fragment-b"], "purpose": "fragment excluded from request-target identity"},
        {"id": "query_variation", "kind": "comparison", "statements": ["query-a", "query-b"], "purpose": "query retained as request-target identity"},
        {"id": "redirect_relation", "kind": "comparison", "statements": ["redirect-source", "redirect-final"], "purpose": "redirect is explicit relation, not implicit target merge"},
        {"id": "canonical_alias", "kind": "comparison", "statements": ["canonical-alias", "canonical-final"], "purpose": "HTML canonical is explicit relation, not implicit target merge"},
        {"id": "vary_language", "kind": "comparison", "statements": ["language-en", "language-zh"], "purpose": "Vary representation difference"},
        {"id": "vantage_variation", "kind": "comparison", "statements": ["vantage-us", "vantage-eu"], "purpose": "network-vantage representation difference"},
        {"id": "authentication_variation", "kind": "comparison", "statements": ["auth-public", "auth-private"], "purpose": "authentication representation difference"},
        {"id": "repeated_observation", "kind": "comparison", "statements": ["repeated-a", "repeated-b"], "purpose": "same bytes across capture activities"},
        {"id": "ordered_temporal_variation", "kind": "comparison", "statements": ["temporal-old", "temporal-new"], "purpose": "ordered changed bytes with causal receipt"},
        {"id": "parallel_observation", "kind": "comparison", "statements": ["parallel-a", "parallel-b"], "purpose": "overlapping independent time intervals without causal predecessor"},
        {"id": "clock_skew_local_declarations", "kind": "comparison", "statements": ["clock-skew-a", "clock-skew-b"], "purpose": "local clocks cannot create temporal proof"},
        {"id": "tampered_wacz", "kind": "statement", "statements": ["tampered-wacz"], "purpose": "WACZ manifest mismatch invalidates statement"},
        {"id": "inconsistent_agent_disclosure", "kind": "statement", "statements": ["agent-binding-error"], "purpose": "issuer and verification method mismatch"},
        {"id": "missing_history_complete_scope", "kind": "history-membership", "statements": ["missing-history-statement"], "history_views": ["complete-history"], "purpose": "complete declared scope permits MISSING_HISTORY"},
        {"id": "partial_history_absence", "kind": "history-membership", "statements": ["partial-history-statement"], "history_views": ["partial-history"], "purpose": "partial scope cannot prove absence"},
        {"id": "contradictory_checkpoints", "kind": "equivocation", "history_views": ["equivocation-left", "equivocation-right"], "purpose": "same log and tree size, different signed root hashes"},
        {"id": "valid_statement_import", "kind": "import", "statements": ["imported-valid"], "purpose": "valid external statement can be imported without rewriting capture agency"},
    ]
    expected = {
        "profile_version": "IWOH-0.1",
        "assertion_fields": ["target_identity", "target_relation", "statement_validity", "comparability", "relationship", "history_membership", "completeness_scope", "statement_import_validity", "equivocation_status"],
        "scenarios": {
            "fragment_identity": result("SAME_REQUEST_TARGET", "EXACT_REQUEST_TARGET", {"fragment-a": "VALID", "fragment-b": "VALID"}, "COMPARABLE", "REPEATED_OBSERVATION"),
            "query_variation": result("DIFFERENT_REQUEST_TARGETS", "DISTINCT_REQUEST_TARGETS", {"query-a": "VALID", "query-b": "VALID"}, "INCOMPARABLE", "INCOMPARABLE"),
            "redirect_relation": result("DIFFERENT_REQUEST_TARGETS", "RELATED_TARGET", {"redirect-source": "VALID", "redirect-final": "VALID"}, "INCOMPARABLE", "INCOMPARABLE"),
            "canonical_alias": result("DIFFERENT_REQUEST_TARGETS", "RELATED_TARGET", {"canonical-alias": "VALID", "canonical-final": "VALID"}, "INCOMPARABLE", "INCOMPARABLE"),
            "vary_language": result("SAME_REQUEST_TARGET", "EXACT_REQUEST_TARGET", {"language-en": "VALID", "language-zh": "VALID"}, "INCOMPARABLE", "REPRESENTATION_VARIATION"),
            "vantage_variation": result("SAME_REQUEST_TARGET", "EXACT_REQUEST_TARGET", {"vantage-us": "VALID", "vantage-eu": "VALID"}, "INCOMPARABLE", "REPRESENTATION_VARIATION"),
            "authentication_variation": result("SAME_REQUEST_TARGET", "EXACT_REQUEST_TARGET", {"auth-public": "VALID", "auth-private": "VALID"}, "INCOMPARABLE", "REPRESENTATION_VARIATION"),
            "repeated_observation": result("SAME_REQUEST_TARGET", "EXACT_REQUEST_TARGET", {"repeated-a": "VALID", "repeated-b": "VALID"}, "COMPARABLE", "REPEATED_OBSERVATION"),
            "ordered_temporal_variation": result("SAME_REQUEST_TARGET", "EXACT_REQUEST_TARGET", {"temporal-old": "VALID", "temporal-new": "VALID"}, "COMPARABLE", "TEMPORAL_VARIATION"),
            "parallel_observation": result("SAME_REQUEST_TARGET", "EXACT_REQUEST_TARGET", {"parallel-a": "VALID", "parallel-b": "VALID"}, "COMPARABLE", "PARALLEL_OBSERVATION"),
            "clock_skew_local_declarations": result("SAME_REQUEST_TARGET", "EXACT_REQUEST_TARGET", {"clock-skew-a": "VALID", "clock-skew-b": "VALID"}, "COMPARABLE", "UNKNOWN"),
            "tampered_wacz": result("NOT_APPLICABLE", "NOT_APPLICABLE", {"tampered-wacz": "INVALID_ARCHIVE_DIGEST"}, "NOT_APPLICABLE", "NOT_APPLICABLE"),
            "inconsistent_agent_disclosure": result("NOT_APPLICABLE", "NOT_APPLICABLE", {"agent-binding-error": "INVALID_AGENT_BINDING"}, "NOT_APPLICABLE", "NOT_APPLICABLE"),
            "missing_history_complete_scope": result("NOT_APPLICABLE", "NOT_APPLICABLE", {"missing-history-statement": "VALID"}, "NOT_APPLICABLE", "NOT_APPLICABLE", "MISSING_HISTORY", "COMPLETE_FOR_DECLARED_SCOPE"),
            "partial_history_absence": result("NOT_APPLICABLE", "NOT_APPLICABLE", {"partial-history-statement": "VALID"}, "NOT_APPLICABLE", "NOT_APPLICABLE", "HISTORY_ABSENCE_UNPROVEN", "PARTIAL"),
            "contradictory_checkpoints": result("NOT_APPLICABLE", "NOT_APPLICABLE", {"equivocation-left": "VALID", "equivocation-right": "VALID"}, "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE", "COMPLETE_FOR_DECLARED_SCOPE", "NOT_APPLICABLE", "EQUIVOCATION_DETECTED"),
            "valid_statement_import": result("NOT_APPLICABLE", "NOT_APPLICABLE", {"imported-valid": "VALID"}, "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE", "IMPORTED_VALID"),
        },
    }
    write_json(ROOT / "scenarios.json", {"profile_version": "IWOH-0.1", "scenarios": scenarios})
    write_json(ROOT / "expected_results.json", expected)
    write_json(ROOT / "README.md", {
        "generated_by": "tools_generate_fixtures.py",
        "profile_version": "IWOH-0.1",
        "artifact_count": len(artifacts),
        "statement_count": len(statements),
        "scenario_count": len(scenarios),
        "history_count": 4,
        "receipt_count": 4,
        "offline_only": True,
    })


if __name__ == "__main__":
    build()
    print(f"Generated IWOH fixture corpus at {ROOT}")
