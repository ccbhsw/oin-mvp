#!/usr/bin/env python3
"""Independent implementation A of the IWOH v0.1 verifier.

This source deliberately does not import any OIN component or corpus generator.
It consumes only the Profile's static fixture layout, public key registry and
scenario inputs.  It implements a restricted RFC 8785 path valid for the corpus
(I-JSON primitive types; no floating point values) and W3C eddsa-jcs-2022.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ASSERTION_FIELDS = (
    "target_identity", "target_relation", "statement_validity", "comparability",
    "relationship", "history_membership", "completeness_scope",
    "statement_import_validity", "equivocation_status",
)


class VerificationFailure(Exception):
    pass


def sha256_prefixed(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonicalize(value: Any) -> bytes:
    """RFC 8785-compatible serialization for the fixture's I-JSON subset.

    The corpus uses no floats and all member names are ASCII, eliminating the
    ECMAScript numeric and non-BMP sorting edge cases.  Reject unsupported
    numbers rather than silently producing a non-JCS result.
    """
    def reject_float(item: Any) -> None:
        if isinstance(item, float):
            raise VerificationFailure("JCS_FLOAT_UNSUPPORTED_FOR_FIXTURE")
        if isinstance(item, dict):
            for child in item.values():
                reject_float(child)
        elif isinstance(item, list):
            for child in item:
                reject_float(child)
    reject_float(value)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def base58_decode(text: str) -> bytes:
    if not text or text[0] != "z":
        raise VerificationFailure("MULTIBASE_PREFIX_ERROR")
    accumulator = 0
    for char in text[1:].encode("ascii"):
        try:
            index = ALPHABET.index(char)
        except ValueError as error:
            raise VerificationFailure("BASE58_DECODE_ERROR") from error
        accumulator = accumulator * 58 + index
    raw = accumulator.to_bytes((accumulator.bit_length() + 7) // 8, "big") if accumulator else b""
    leading = len(text[1:]) - len(text[1:].lstrip("1"))
    return b"\0" * leading + raw


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class ProfileVerifierA:
    def __init__(self, corpus: Path) -> None:
        self.corpus = corpus
        keys = load_json(corpus / "keys" / "public_keys.json")["verification_methods"]
        self.key_map = {item["id"]: item for item in keys}
        trust = load_json(corpus / "trust_registry.json")
        self.trusted_controllers = set(trust["trusted_assertion_method_controllers"])
        self.trusted_time_receipt_issuers = set(trust["trusted_time_receipt_issuers"])
        self.trusted_history_issuers = set(trust["trusted_history_issuers"])
        self.statements: dict[str, dict[str, Any]] = {}
        self.statement_paths = {path.stem: path for path in (corpus / "statements").glob("*.json")}
        self.history_paths = {path.stem: path for path in (corpus / "history").glob("*.json")}
        self.receipt_paths = {path.stem: path for path in (corpus / "receipts").glob("*.json")}

    def _verify_proof(self, document: dict[str, Any], *, require_trusted_controller: bool = True) -> str:
        proof = document.get("proof")
        if not isinstance(proof, dict):
            return "INVALID_SIGNATURE"
        if proof.get("type") != "DataIntegrityProof" or proof.get("cryptosuite") != "eddsa-jcs-2022":
            return "INVALID_SIGNATURE"
        if proof.get("proofPurpose") != "assertionMethod":
            return "INVALID_SIGNATURE"
        method_id = proof.get("verificationMethod")
        method = self.key_map.get(method_id)
        if not method:
            return "INVALID_SIGNATURE"
        proof_value = proof.get("proofValue")
        if not isinstance(proof_value, str):
            return "INVALID_SIGNATURE"
        try:
            signature = base58_decode(proof_value)
            key_material = base58_decode(method["publicKeyMultibase"])
            if not key_material.startswith(b"\xed\x01") or len(key_material) != 34:
                return "INVALID_SIGNATURE"
            unsecured = copy.deepcopy(document)
            unsecured.pop("proof", None)
            proof_options = copy.deepcopy(proof)
            proof_options.pop("proofValue", None)
            if "@context" in proof_options:
                doc_context = unsecured.get("@context", [])
                proof_context = proof_options["@context"]
                if doc_context[: len(proof_context)] != proof_context:
                    return "INVALID_SIGNATURE"
                unsecured["@context"] = proof_context
            hash_data = hashlib.sha256(canonicalize(proof_options)).digest() + hashlib.sha256(canonicalize(unsecured)).digest()
            Ed25519PublicKey.from_public_bytes(key_material[2:]).verify(signature, hash_data)
        except (InvalidSignature, ValueError, TypeError, UnicodeError, VerificationFailure):
            return "INVALID_SIGNATURE"
        if document.get("issuer") != method.get("controller"):
            return "INVALID_AGENT_BINDING"
        if require_trusted_controller and method.get("controller") not in self.trusted_controllers:
            return "INVALID_AGENT_BINDING"
        return "VALID"

    def _load_statement(self, name: str) -> dict[str, Any]:
        if name not in self.statements:
            self.statements[name] = load_json(self.statement_paths[name])
        return self.statements[name]

    def _validate_wacz_and_payload(self, statement: dict[str, Any]) -> str:
        evidence = statement.get("evidence", {})
        try:
            relative = evidence["artifact"]
            artifact_path = self.corpus / relative
            artifact_bytes = artifact_path.read_bytes()
            if sha256_prefixed(artifact_bytes) != evidence.get("wacz_digest"):
                return "INVALID_ARCHIVE_DIGEST"
            with zipfile.ZipFile(artifact_path) as package:
                manifest_bytes = package.read("datapackage.json")
                digest_info = json.loads(package.read("datapackage-digest.json"))
                if digest_info.get("path") != "datapackage.json" or digest_info.get("hash") != sha256_prefixed(manifest_bytes):
                    return "INVALID_ARCHIVE_DIGEST"
                manifest = json.loads(manifest_bytes)
                if manifest.get("profile") != "data-package" or manifest.get("wacz_version") != "1.1.1":
                    return "INVALID_ARCHIVE_DIGEST"
                for resource in manifest.get("resources", []):
                    data = package.read(resource["path"])
                    if len(data) != resource.get("bytes") or sha256_prefixed(data) != resource.get("hash"):
                        return "INVALID_ARCHIVE_DIGEST"
                warc = package.read("archive/data.warc")
        except (OSError, KeyError, ValueError, zipfile.BadZipFile, json.JSONDecodeError):
            return "EVIDENCE_UNAVAILABLE"
        record_marker = ("WARC-Record-ID: <" + evidence.get("warc_record_id", "") + ">\r\n").encode("utf-8")
        if record_marker not in warc:
            return "INVALID_PAYLOAD_DIGEST"
        try:
            header_end = warc.index(b"\r\n\r\n")
            record_headers = warc[:header_end].decode("utf-8")
            content_length = None
            for line in record_headers.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    content_length = int(line.split(":", 1)[1].strip())
                    break
            if content_length is None:
                return "INVALID_PAYLOAD_DIGEST"
            http_message = warc[header_end + 4: header_end + 4 + content_length]
            http_end = http_message.index(b"\r\n\r\n")
            payload = http_message[http_end + 4:]
        except (UnicodeDecodeError, ValueError):
            return "INVALID_PAYLOAD_DIGEST"
        payload_digest = sha256_prefixed(payload)
        if payload_digest != evidence.get("payload_digest") or payload_digest != statement.get("response", {}).get("payload_digest"):
            return "INVALID_PAYLOAD_DIGEST"
        if len(payload) != statement.get("response", {}).get("body_byte_length"):
            return "INVALID_PAYLOAD_DIGEST"
        return "VALID"

    def _validate_time_evidence(self, statement: dict[str, Any]) -> str:
        time_evidence = statement.get("time_evidence", {})
        kind = time_evidence.get("kind")
        if kind != "causal-receipt":
            return "VALID"
        relative = time_evidence.get("receipt")
        if not isinstance(relative, str):
            return "INVALID_EXTERNAL_EVIDENCE"
        try:
            receipt = load_json(self.corpus / relative)
        except (OSError, json.JSONDecodeError):
            return "INVALID_EXTERNAL_EVIDENCE"
        status = self._verify_proof(receipt)
        if status != "VALID" or receipt.get("issuer") not in self.trusted_time_receipt_issuers:
            return "INVALID_EXTERNAL_EVIDENCE"
        if receipt.get("statement_id") != statement.get("id"):
            return "INVALID_EXTERNAL_EVIDENCE"
        interval = receipt.get("interval", {})
        if not (interval.get("not_before") and interval.get("not_after") and isinstance(receipt.get("ordinal"), int)):
            return "INVALID_EXTERNAL_EVIDENCE"
        return "VALID"

    def validate_statement(self, name: str) -> str:
        statement = self._load_statement(name)
        proof_status = self._verify_proof(statement)
        if proof_status != "VALID":
            return proof_status
        artifact_status = self._validate_wacz_and_payload(statement)
        if artifact_status != "VALID":
            return artifact_status
        return self._validate_time_evidence(statement)

    def validate_history(self, name: str) -> tuple[str, dict[str, Any]]:
        document = load_json(self.history_paths[name])
        status = self._verify_proof(document)
        if status == "VALID" and document.get("issuer") not in self.trusted_history_issuers:
            status = "INVALID_AGENT_BINDING"
        return status, document

    @staticmethod
    def request_target(statement: dict[str, Any]) -> str:
        return statement["request_target"]["uri"]

    @staticmethod
    def _headers(statement: dict[str, Any], name: str) -> dict[str, str]:
        source = statement.get(name, {})
        return {str(k).lower(): str(v) for k, v in source.items()}

    def target_relation(self, first: dict[str, Any], second: dict[str, Any]) -> tuple[str, str]:
        first_target = self.request_target(first)
        second_target = self.request_target(second)
        if first_target == second_target:
            return "SAME_REQUEST_TARGET", "EXACT_REQUEST_TARGET"
        for source, other in ((first, second), (second, first)):
            source_target = self.request_target(source)
            other_target = self.request_target(other)
            for relation in source.get("target_relations", []):
                if relation.get("from") == source_target and relation.get("to") == other_target and relation.get("asserted_by") in {"response", "archive", "external-signer"}:
                    return "DIFFERENT_REQUEST_TARGETS", "RELATED_TARGET"
        return "DIFFERENT_REQUEST_TARGETS", "DISTINCT_REQUEST_TARGETS"

    def context_reason(self, first: dict[str, Any], second: dict[str, Any]) -> str | None:
        first_context = first["request_context"]
        second_context = second["request_context"]
        if first_context.get("authentication_class") != second_context.get("authentication_class"):
            return "AUTH_CONTEXT_MISMATCH"
        first_vantage = first_context.get("network_vantage", {})
        second_vantage = second_context.get("network_vantage", {})
        if first_vantage.get("id") != second_vantage.get("id"):
            if not (first_vantage.get("vantage_effect") == second_vantage.get("vantage_effect") == "NONE_EXPECTED"):
                return "VANTAGE_MISMATCH"
        first_headers = self._headers(first, "response").get("recorded_response_headers", {})
        second_headers = self._headers(second, "response").get("recorded_response_headers", {})
        # response headers are nested differently; normalize explicitly.
        first_response_headers = {k.lower(): v for k, v in first["response"].get("recorded_response_headers", {}).items()}
        second_response_headers = {k.lower(): v for k, v in second["response"].get("recorded_response_headers", {}).items()}
        vary_values = set()
        for value in (first_response_headers.get("vary", ""), second_response_headers.get("vary", "")):
            vary_values.update(header.strip().lower() for header in value.split(",") if header.strip())
        first_request = {k.lower(): str(v) for k, v in first_context.get("recorded_request_headers", {}).items()}
        second_request = {k.lower(): str(v) for k, v in second_context.get("recorded_request_headers", {}).items()}
        for header in vary_values:
            if header not in first_request or header not in second_request or first_request[header] != second_request[header]:
                return "VARY_VALUE_MISMATCH"
        if first_context.get("capture_policy") != second_context.get("capture_policy"):
            return "CAPTURE_POLICY_MISMATCH"
        if first.get("capture_context_completeness") != "COMPLETE_FOR_REPRESENTATION_SELECTION" or second.get("capture_context_completeness") != "COMPLETE_FOR_REPRESENTATION_SELECTION":
            return "INCOMPLETE_CONTEXT"
        if first_context.get("method") != second_context.get("method"):
            return "METHOD_MISMATCH"
        return None

    def load_receipt(self, statement: dict[str, Any]) -> dict[str, Any] | None:
        time_evidence = statement.get("time_evidence", {})
        if time_evidence.get("kind") != "causal-receipt":
            return None
        try:
            receipt = load_json(self.corpus / time_evidence["receipt"])
        except (OSError, KeyError, json.JSONDecodeError):
            return None
        return receipt if self._verify_proof(receipt) == "VALID" else None

    def relationship(self, first_name: str, second_name: str, statuses: dict[str, str]) -> tuple[str, str]:
        first = self._load_statement(first_name)
        second = self._load_statement(second_name)
        identity, relation = self.target_relation(first, second)
        if any(status != "VALID" for status in statuses.values()):
            return "INCOMPARABLE", "INCOMPARABLE"
        context = self.context_reason(first, second)
        if context is not None:
            if identity == "SAME_REQUEST_TARGET" and first["response"]["payload_digest"] != second["response"]["payload_digest"] and context in {"AUTH_CONTEXT_MISMATCH", "VANTAGE_MISMATCH", "VARY_VALUE_MISMATCH", "CAPTURE_POLICY_MISMATCH"}:
                return "INCOMPARABLE", "REPRESENTATION_VARIATION"
            return "INCOMPARABLE", "INCOMPARABLE"
        if identity != "SAME_REQUEST_TARGET":
            return "INCOMPARABLE", "INCOMPARABLE"
        if first["response"]["payload_digest"] == second["response"]["payload_digest"]:
            return "COMPARABLE", "REPEATED_OBSERVATION"
        first_receipt = self.load_receipt(first)
        second_receipt = self.load_receipt(second)
        if not first_receipt or not second_receipt:
            return "COMPARABLE", "UNKNOWN"
        first_interval = first_receipt["interval"]
        second_interval = second_receipt["interval"]
        first_before, first_after = first_interval["not_before"], first_interval["not_after"]
        second_before, second_after = second_interval["not_before"], second_interval["not_after"]
        first_id, second_id = first["id"], second["id"]
        first_predecessors = set(first_receipt.get("predecessor_statement_ids", []))
        second_predecessors = set(second_receipt.get("predecessor_statement_ids", []))
        ordered = (first_after < second_before and first_id in second_predecessors) or (second_after < first_before and second_id in first_predecessors)
        if ordered:
            return "COMPARABLE", "TEMPORAL_VARIATION"
        overlap = first_before <= second_after and second_before <= first_after
        if overlap and first_id not in second_predecessors and second_id not in first_predecessors:
            return "COMPARABLE", "PARALLEL_OBSERVATION"
        return "COMPARABLE", "UNKNOWN"

    @staticmethod
    def empty_result() -> dict[str, Any]:
        return {
            "target_identity": "NOT_APPLICABLE",
            "target_relation": "NOT_APPLICABLE",
            "statement_validity": {},
            "comparability": "NOT_APPLICABLE",
            "relationship": "NOT_APPLICABLE",
            "history_membership": "NOT_APPLICABLE",
            "completeness_scope": "NOT_APPLICABLE",
            "statement_import_validity": "NOT_APPLICABLE",
            "equivocation_status": "NOT_APPLICABLE",
        }

    def evaluate(self, scenario: dict[str, Any]) -> dict[str, Any]:
        outcome = self.empty_result()
        kind = scenario["kind"]
        statements = scenario.get("statements", [])
        if statements:
            outcome["statement_validity"] = {name: self.validate_statement(name) for name in statements}
        if kind == "comparison":
            first, second = statements
            identity, relation = self.target_relation(self._load_statement(first), self._load_statement(second))
            comparability, relationship = self.relationship(first, second, outcome["statement_validity"])
            outcome.update({"target_identity": identity, "target_relation": relation, "comparability": comparability, "relationship": relationship})
        elif kind == "history-membership":
            history_name = scenario["history_views"][0]
            history_status, history = self.validate_history(history_name)
            if history_status != "VALID":
                outcome["completeness_scope"] = "UNKNOWN"
                outcome["history_membership"] = "HISTORY_ABSENCE_UNPROVEN"
            else:
                completeness = history.get("completeness", "UNKNOWN")
                outcome["completeness_scope"] = completeness
                sought = self._load_statement(statements[0])["id"]
                in_history = sought in set(history.get("statement_ids", []))
                outcome["history_membership"] = "PRESENT" if in_history else ("MISSING_HISTORY" if completeness == "COMPLETE_FOR_DECLARED_SCOPE" else "HISTORY_ABSENCE_UNPROVEN")
        elif kind == "equivocation":
            statuses: dict[str, str] = {}
            views: list[dict[str, Any]] = []
            for name in scenario["history_views"]:
                status, view = self.validate_history(name)
                statuses[name] = status
                views.append(view)
            outcome["statement_validity"] = statuses
            outcome["completeness_scope"] = "COMPLETE_FOR_DECLARED_SCOPE" if all(view.get("completeness") == "COMPLETE_FOR_DECLARED_SCOPE" for view in views) else "UNKNOWN"
            left, right = views
            left_checkpoint, right_checkpoint = left.get("checkpoint", {}), right.get("checkpoint", {})
            same_position = left_checkpoint.get("log_id") == right_checkpoint.get("log_id") and left_checkpoint.get("tree_size") == right_checkpoint.get("tree_size")
            outcome["equivocation_status"] = "EQUIVOCATION_DETECTED" if all(status == "VALID" for status in statuses.values()) and same_position and left_checkpoint.get("root_hash") != right_checkpoint.get("root_hash") else "EQUIVOCATION_NOT_DETECTABLE"
        elif kind == "import":
            status = outcome["statement_validity"][statements[0]]
            outcome["statement_import_validity"] = "IMPORTED_VALID" if status == "VALID" else "REJECTED_INVALID"
        return outcome


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path(__file__).resolve().parents[1] / "fixtures")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenarios = load_json(args.corpus / "scenarios.json")["scenarios"]
    verifier = ProfileVerifierA(args.corpus)
    results = {scenario["id"]: verifier.evaluate(scenario) for scenario in scenarios}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"implementation": "A-python-stdlib-zipfile-cryptography", "profile_version": "IWOH-0.1", "assertion_fields": list(ASSERTION_FIELDS), "results": results}, indent=2) + "\n", encoding="utf-8")
    print(f"implementation=A scenarios={len(results)} output={args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
