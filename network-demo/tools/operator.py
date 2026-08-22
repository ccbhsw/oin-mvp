#!/usr/bin/env python3
"""Local OIN network-demo operator commands built on the existing OIN MVP core.

This program creates physically separate local operator data roots.  It does not
introduce a new evidence format: capture, manifest signing, WARC/WACZ creation,
and offline verification are delegated to the existing ``oin`` modules.
"""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx

from oin.capture.http_capture import CaptureSafetyError, capture_url
from oin.identity.keys import load_private_key, sign_json, verify_json, write_keypair
from oin.observation.service import build_observation, export_bundle
from oin.protocol.core import canonical_json, canonicalize_url, sha256_prefixed, utc_now
from oin.verifier.offline import verify_bundle

MAX_IMPORT_PACKAGE_BYTES = 32 * 1024 * 1024
MAX_IMPORT_MEMBER_BYTES = 16 * 1024 * 1024
MAX_IMPORT_TOTAL_UNCOMPRESSED_BYTES = 32 * 1024 * 1024
MAX_IMPORT_MEMBER_COUNT = 16

RUNTIME_DIRECTORIES = (
    "identity",
    "keys",
    "descriptors",
    "captures",
    "evidence",
    "manifests",
    "statements",
    "verification-results",
    "replication-records",
    "exports",
    "imports",
    "recovery",
)


def stable_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value) + b"\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in value)


def ensure_operator_root(root: Path) -> None:
    for name in RUNTIME_DIRECTORIES:
        (root / name).mkdir(parents=True, exist_ok=True)


def identity_path(root: Path) -> Path:
    return root / "identity" / "operator.json"


def require_identity(root: Path) -> dict[str, Any]:
    path = identity_path(root)
    if not path.exists():
        raise SystemExit(f"operator identity is missing: run init first for {root}")
    return read_json(path)


def verification_status(result: dict[str, Any]) -> str:
    if result.get("status") == "VALID":
        return "VERIFIED"
    checks = result.get("checks", {})
    if checks.get("observer_signature") is False:
        return "INVALID_SIGNATURE"
    if any(checks.get(name) is False for name in ("archive_hash", "raw_content_hash", "raw_content_bytes", "manifest_id")):
        return "INVALID_BINDING"
    return "MALFORMED_ARTIFACT"


def command_init(args: argparse.Namespace) -> int:
    root = args.operator_root.resolve()
    ensure_operator_root(root)
    private_path = root / "keys" / "observer-private.pem"
    if private_path.exists() and not args.force:
        raise SystemExit(f"private key already exists at {private_path}; use --force only to rotate intentionally")
    if private_path.exists():
        for filename in ("observer-private.pem", "observer-public.json"):
            candidate = root / "keys" / filename
            if candidate.exists():
                candidate.unlink()
    public = write_keypair(root / "keys", operator_metadata={"operator_id": args.operator_id})
    os.chmod(private_path, 0o600)
    identity = {
        "identity_version": "1.0",
        "operator_id": args.operator_id,
        "observer_id": public["observer_id"],
        "created_at": public["created_at"],
        "local_simulation": True,
        "public_key_path": "keys/observer-public.json",
    }
    descriptor = {
        "descriptor_version": "1.0",
        "operator_id": args.operator_id,
        "descriptor_revision": args.descriptor_revision,
        "published_at": utc_now(),
        "public_key": {
            "algorithm": "Ed25519",
            "key_id": public["observer_id"],
            "public_key_base64": public["public_key"],
        },
        "capabilities": ["capture-http", "verify-offline", "export-bundle", "import-bundle", "history-view", "recovery"],
        "supported_artifact_types": ["application/wacz", "application/warc", "application/zip"],
        "endpoint": {"transport": "file", "base_url": str(root)},
    }
    stable_write(identity_path(root), identity)
    stable_write(root / "descriptors" / "operator-descriptor.json", descriptor)
    print(json.dumps({"status": "INITIALIZED", "operator": identity, "descriptor": descriptor}, sort_keys=True))
    return 0


def command_capture(args: argparse.Namespace) -> int:
    root = args.operator_root.resolve()
    ensure_operator_root(root)
    identity = require_identity(root)
    try:
        capture = capture_url(args.url, timeout_seconds=args.timeout_seconds)
    except httpx.TimeoutException as exc:
        print(json.dumps({"status": "TIMEOUT", "target": args.url, "detail": str(exc)}, sort_keys=True))
        return 1
    except CaptureSafetyError as exc:
        print(json.dumps({"status": "REJECTED_TARGET", "target": args.url, "detail": str(exc)}, sort_keys=True))
        return 1
    except httpx.HTTPError as exc:
        print(json.dumps({"status": "UNAVAILABLE", "target": args.url, "detail": str(exc)}, sort_keys=True))
        return 1

    private = load_private_key(root / "keys" / "observer-private.pem")
    manifest, archive = build_observation(capture, private, archive_format=args.archive_format)
    observation_id = manifest["observation_id"]
    file_id = safe_name(observation_id)
    bundle_directory = root / "evidence" / file_id
    evidence = {
        "timestamp": {
            "kind": "local-declaration",
            "message_imprint": sha256_prefixed(canonical_json(manifest)),
        }
    }
    export_bundle(bundle_directory, manifest, archive, evidence)
    stable_write(root / "manifests" / f"{file_id}.json", manifest)
    stable_write(root / "statements" / f"{file_id}.json", manifest)
    capture_record = {
        "capture_record_version": "1.0",
        "observation_id": observation_id,
        "operator_id": identity["operator_id"],
        "requested_url": capture.requested_url,
        "observed_url": capture.observed_url,
        "capture_time": capture.captured_at,
        "capture_method": "http-get",
        "http_status": capture.http_status,
        "http_headers": capture.http_headers,
        "redirect_chain": capture.redirect_chain,
        "response_bytes": len(capture.body),
        "archive_format": args.archive_format,
        "archive_digest": manifest["content"]["archive_hash"],
        "manifest_digest": sha256_prefixed(canonical_json(manifest)),
    }
    stable_write(root / "captures" / f"{file_id}.json", capture_record)
    result = verify_bundle(bundle_directory)
    verification = {
        "verification_record_version": "1.0",
        "verified_at": utc_now(),
        "verification_status": verification_status(result),
        "offline_result": result,
        "bundle_relative_path": str(bundle_directory.relative_to(root)),
    }
    stable_write(root / "verification-results" / f"{file_id}.json", verification)
    print(
        json.dumps(
            {
                "status": "CAPTURED" if result.get("status") == "VALID" else verification["verification_status"],
                "operator_id": identity["operator_id"],
                "observation_id": observation_id,
                "http_status": capture.http_status,
                "archive_digest": manifest["content"]["archive_hash"],
                "bundle": str(bundle_directory),
                "verification": verification["verification_status"],
            },
            sort_keys=True,
        )
    )
    return 0 if result.get("status") == "VALID" else 1


def command_verify(args: argparse.Namespace) -> int:
    bundle = args.bundle.resolve()
    try:
        result = verify_bundle(bundle)
    except FileNotFoundError as exc:
        print(json.dumps({"status": "NOT_FOUND", "bundle": str(bundle), "detail": str(exc)}, sort_keys=True))
        return 1
    output = {"status": verification_status(result), "bundle": str(bundle), "offline_result": result}
    print(json.dumps(output, sort_keys=True))
    return 0 if output["status"] == "VERIFIED" else 1


def observation_bundle(root: Path, observation_id: str) -> tuple[Path, dict[str, Any]]:
    bundle = root / "evidence" / safe_name(observation_id)
    manifest_path = bundle / "observation.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"observation bundle is not available: {observation_id}")
    return bundle, read_json(manifest_path)


def command_export(args: argparse.Namespace) -> int:
    root = args.operator_root.resolve()
    identity = require_identity(root)
    try:
        bundle, observation = observation_bundle(root, args.observation_id)
    except FileNotFoundError as exc:
        print(json.dumps({"status": "NOT_FOUND", "detail": str(exc)}, sort_keys=True))
        return 1
    archive_format = observation["content"]["archive_format"]
    archive_name = f"raw.{archive_format}"
    files = ["observation.json", archive_name, "observer-public.json"]
    if (bundle / "evidence.json").exists():
        files.append("evidence.json")
    exporter_public_path = root / "keys" / "observer-public.json"
    digest_map = {name: sha256_prefixed((bundle / name).read_bytes()) for name in files}
    descriptor_path = root / "descriptors" / "operator-descriptor.json"
    descriptor = read_json(descriptor_path)
    export_manifest = {
        "export_version": "1.0",
        "exported_at": utc_now(),
        "source_operator": identity["operator_id"],
        "exporter_observer_id": identity["observer_id"],
        "descriptor_revision": descriptor["descriptor_revision"],
        "descriptor_digest": sha256_prefixed(descriptor_path.read_bytes()),
        "observation_id": observation["observation_id"],
        "original_issuer": observation["observer"]["observer_id"],
        "artifact": {
            "filename": archive_name,
            "digest": observation["content"]["archive_hash"],
            "media_type": observation["content"]["archive_media_type"],
        },
        "manifest": {"filename": "observation.json", "digest": digest_map["observation.json"]},
        "bundle_files": digest_map,
    }
    private = load_private_key(root / "keys" / "observer-private.pem")
    export_signature = {"algorithm": "Ed25519", "signed": "export-manifest.json", "value": sign_json(private, export_manifest)}
    output = args.output.resolve() if args.output else root / "exports" / f"{safe_name(observation['observation_id'])}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name in files:
            package.write(bundle / name, f"bundle/{name}")
        package.write(descriptor_path, "operator-descriptor.json")
        package.write(exporter_public_path, "exporter-public.json")
        package.writestr("export-manifest.json", canonical_json(export_manifest))
        package.writestr("export-signature.json", canonical_json(export_signature))
    print(
        json.dumps(
            {
                "status": "EXPORTED",
                "source_operator": identity["operator_id"],
                "original_issuer": export_manifest["original_issuer"],
                "observation_id": observation["observation_id"],
                "export": str(output),
                "export_digest": sha256_prefixed(output.read_bytes()),
            },
            sort_keys=True,
        )
    )
    return 0


def safe_extract_member(package: zipfile.ZipFile, member: str) -> bytes:
    member_path = Path(member)
    if member_path.is_absolute() or ".." in member_path.parts or "\\" in member:
        raise ValueError("unsafe ZIP member path")
    try:
        info = package.getinfo(member)
    except KeyError as exc:
        raise ValueError(f"ZIP member is missing: {member}") from exc
    if info.is_dir() or info.file_size > MAX_IMPORT_MEMBER_BYTES:
        raise ValueError("ZIP member exceeds safe import limits")
    return package.read(info)


def validate_export_package_limits(package: zipfile.ZipFile) -> None:
    infos = package.infolist()
    names = [info.filename for info in infos]
    if len(infos) > MAX_IMPORT_MEMBER_COUNT or len(names) != len(set(names)):
        raise ValueError("ZIP package member count is unsafe")
    if any(info.is_dir() or "\\" in info.filename or Path(info.filename).is_absolute() or ".." in Path(info.filename).parts for info in infos):
        raise ValueError("ZIP package contains an unsafe member path")
    if any(info.file_size > MAX_IMPORT_MEMBER_BYTES for info in infos):
        raise ValueError("ZIP package member exceeds safe import limits")
    if sum(info.file_size for info in infos) > MAX_IMPORT_TOTAL_UNCOMPRESSED_BYTES:
        raise ValueError("ZIP package exceeds safe uncompressed size limit")


def import_failure_status(error: Exception) -> str:
    detail = str(error).lower()
    if "signature" in detail:
        return "INVALID_SIGNATURE"
    if "binding" in detail or "digest" in detail or "hash" in detail or "identity" in detail:
        return "INVALID_BINDING"
    if "not found" in detail or "missing" in detail:
        return "NOT_FOUND"
    return "MALFORMED_ARTIFACT"


def write_replication_record(root: Path, record: dict[str, Any]) -> Path:
    path = root / "replication-records" / f"{safe_name(record['record_id'])}.json"
    stable_write(path, record)
    return path


def command_import(args: argparse.Namespace) -> int:
    root = args.operator_root.resolve()
    ensure_operator_root(root)
    identity = require_identity(root)
    source = args.export.resolve()
    export_digest = sha256_prefixed(source.read_bytes()) if source.exists() else None
    now = utc_now()
    original_digest: str | None = None
    original_manifest_digest: str | None = None
    original_issuer: str | None = None
    receipt_id = f"import-{safe_name(export_digest or 'missing')}-{safe_name(identity['operator_id'])}"
    try:
        if not source.exists():
            raise FileNotFoundError("export artifact is missing")
        if source.stat().st_size > MAX_IMPORT_PACKAGE_BYTES:
            raise ValueError("export artifact exceeds safe import size limit")
        with zipfile.ZipFile(source, "r") as package:
            validate_export_package_limits(package)
            required = {"bundle/observation.json", "bundle/observer-public.json", "operator-descriptor.json", "exporter-public.json", "export-manifest.json", "export-signature.json"}
            names = set(package.namelist())
            if not required.issubset(names):
                raise ValueError("export package is missing required members")
            export_manifest = json.loads(safe_extract_member(package, "export-manifest.json"))
            export_signature = json.loads(safe_extract_member(package, "export-signature.json"))
            observation_bytes = safe_extract_member(package, "bundle/observation.json")
            observation = json.loads(observation_bytes)
            archive_name = export_manifest.get("artifact", {}).get("filename", "")
            if archive_name not in {"raw.wacz", "raw.warc"}:
                raise ValueError("export artifact filename is unsupported")
            archive_bytes = safe_extract_member(package, f"bundle/{archive_name}")
            public_bytes = safe_extract_member(package, "bundle/observer-public.json")
            public_document = json.loads(public_bytes)
            exporter_public_bytes = safe_extract_member(package, "exporter-public.json")
            exporter_public = json.loads(exporter_public_bytes)
            descriptor_bytes = safe_extract_member(package, "operator-descriptor.json")
            descriptor = json.loads(descriptor_bytes)
            original_digest = observation.get("content", {}).get("archive_hash")
            original_manifest_digest = sha256_prefixed(observation_bytes)
            original_issuer = observation.get("observer", {}).get("observer_id")
            if not original_digest or not original_issuer:
                raise ValueError("manifest identity binding is missing")
            if canonical_json(public_document) != canonical_json(observation["observer"]):
                raise ValueError("external public key identity binding is invalid")
            if descriptor.get("operator_id") != export_manifest.get("source_operator"):
                raise ValueError("descriptor operator binding is invalid")
            if descriptor.get("public_key", {}).get("public_key_base64") != exporter_public.get("public_key"):
                raise ValueError("descriptor exporter public key binding is invalid")
            if descriptor.get("public_key", {}).get("key_id") != exporter_public.get("observer_id"):
                raise ValueError("descriptor exporter key identifier binding is invalid")
            if export_manifest.get("exporter_observer_id") != exporter_public.get("observer_id"):
                raise ValueError("export signer identity binding is invalid")
            if not verify_json(exporter_public["public_key"], export_manifest, export_signature.get("value", "")):
                raise ValueError("export manifest signature is invalid")
            if export_manifest.get("original_issuer") != original_issuer:
                raise ValueError("original issuer binding is invalid")
            if export_manifest.get("observation_id") != observation.get("observation_id"):
                raise ValueError("observation identifier binding is invalid")
            if export_manifest.get("artifact", {}).get("digest") != original_digest:
                raise ValueError("artifact digest binding is invalid")
            if export_manifest.get("manifest", {}).get("digest") != original_manifest_digest:
                raise ValueError("manifest digest binding is invalid")
            if sha256_prefixed(archive_bytes) != original_digest:
                raise ValueError("artifact bytes digest is invalid")
            if export_manifest.get("descriptor_digest") != sha256_prefixed(descriptor_bytes):
                raise ValueError("descriptor digest binding is invalid")
            bundle_files = export_manifest.get("bundle_files", {})
            for name, expected_digest in bundle_files.items():
                actual = safe_extract_member(package, f"bundle/{name}")
                if sha256_prefixed(actual) != expected_digest:
                    raise ValueError(f"bundle file digest is invalid: {name}")
            with tempfile.TemporaryDirectory() as temporary:
                staged = Path(temporary) / "bundle"
                staged.mkdir()
                for name in bundle_files:
                    (staged / name).write_bytes(safe_extract_member(package, f"bundle/{name}"))
                verified = verify_bundle(staged)
            if verified.get("status") != "VALID":
                raise ValueError(f"offline evidence verification failed: {verification_status(verified)}")

        retained_id = safe_name(observation["observation_id"])
        retained_bundle = root / "evidence" / retained_id
        if retained_bundle.exists():
            shutil.rmtree(retained_bundle)
        retained_bundle.mkdir(parents=True)
        with zipfile.ZipFile(source, "r") as package:
            for name in bundle_files:
                (retained_bundle / name).write_bytes(safe_extract_member(package, f"bundle/{name}"))
        import_copy = root / "imports" / f"{safe_name(export_digest)}.zip"
        shutil.copyfile(source, import_copy)
        stable_write(root / "manifests" / f"{retained_id}.json", observation)
        stable_write(root / "statements" / f"{retained_id}.json", observation)
        verification = {
            "verification_record_version": "1.0",
            "verified_at": utc_now(),
            "verification_status": "VERIFIED",
            "offline_result": verified,
            "bundle_relative_path": str(retained_bundle.relative_to(root)),
        }
        stable_write(root / "verification-results" / f"{retained_id}.json", verification)
        record = {
            "record_version": "1.0",
            "record_id": receipt_id,
            "recorded_at": now,
            "status": "ACCEPTED",
            "original_artifact_digest": original_digest,
            "original_manifest_digest": original_manifest_digest,
            "original_issuer": original_issuer,
            "importer": identity["operator_id"],
            "custodian": identity["operator_id"],
            "replica": identity["operator_id"],
            "source": {"transport": "file", "locator": source.name, "export_digest": export_digest},
            "import_time": now,
            "verification_result": {"status": "VERIFIED", "checks": verified["checks"], "detail": "Verified before retention."},
            "retained_artifact_identity": {"relative_path": str(retained_bundle.relative_to(root)), "artifact_digest": original_digest},
        }
        receipt_path = write_replication_record(root, record)
        print(
            json.dumps(
                {
                    "status": "ACCEPTED",
                    "importer": identity["operator_id"],
                    "original_issuer": original_issuer,
                    "observation_id": observation["observation_id"],
                    "retained_bundle": str(retained_bundle),
                    "replication_record": str(receipt_path),
                },
                sort_keys=True,
            )
        )
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        status = import_failure_status(exc)
        record = {
            "record_version": "1.0",
            "record_id": receipt_id,
            "recorded_at": now,
            "status": "REJECTED",
            "original_artifact_digest": original_digest,
            "original_manifest_digest": original_manifest_digest,
            "original_issuer": original_issuer,
            "importer": identity["operator_id"],
            "custodian": identity["operator_id"],
            "replica": identity["operator_id"],
            "source": {"transport": "file", "locator": source.name, "export_digest": export_digest},
            "import_time": now,
            "verification_result": {"status": status, "checks": {}, "detail": str(exc)},
            "retained_artifact_identity": {"relative_path": None, "artifact_digest": original_digest},
        }
        receipt_path = write_replication_record(root, record)
        print(json.dumps({"status": status, "accepted": False, "detail": str(exc), "replication_record": str(receipt_path)}, sort_keys=True))
        return 1


def command_recover(args: argparse.Namespace) -> int:
    root = args.operator_root.resolve()
    source = args.export.resolve()
    result = command_import(argparse.Namespace(operator_root=root, export=source))
    if result != 0:
        return result
    export_digest = sha256_prefixed(source.read_bytes())
    receipts = sorted((root / "replication-records").glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    accepted = next((read_json(path) for path in receipts if read_json(path).get("status") == "ACCEPTED"), None)
    recovery = {
        "recovery_version": "1.0",
        "recovered_at": utc_now(),
        "operator": require_identity(root)["operator_id"],
        "status": "RECOVERED",
        "source_export_digest": export_digest,
        "original_issuer": accepted.get("original_issuer") if accepted else None,
        "restored_artifact_digest": accepted.get("original_artifact_digest") if accepted else None,
        "replication_record_id": accepted.get("record_id") if accepted else None,
        "local_simulation": True,
    }
    recovery_path = root / "recovery" / f"recovery-{safe_name(export_digest)}.json"
    stable_write(recovery_path, recovery)
    print(json.dumps({"status": "RECOVERED", "operator": recovery["operator"], "recovery_record": str(recovery_path)}, sort_keys=True))
    return 0


def command_set_availability(args: argparse.Namespace) -> int:
    root = args.operator_root.resolve()
    identity = require_identity(root)
    marker = root / "recovery" / "OFFLINE"
    if args.state == "offline":
        marker.write_text("LOCAL_SIMULATION: operator endpoint unavailable\n", encoding="utf-8")
    elif marker.exists():
        marker.unlink()
    print(json.dumps({"status": "OFFLINE" if marker.exists() else "ONLINE", "operator": identity["operator_id"]}, sort_keys=True))
    return 0


def parse_scope(entries: list[str]) -> list[tuple[str, Path]]:
    scope: list[tuple[str, Path]] = []
    for entry in entries:
        if "=" not in entry:
            raise ValueError("each --operator must use OPERATOR_ID=PATH")
        operator_id, raw_path = entry.split("=", 1)
        if not operator_id or not raw_path:
            raise ValueError("each --operator must use OPERATOR_ID=PATH")
        scope.append((operator_id, Path(raw_path).resolve()))
    return scope


def receipt_for_bundle(root: Path, relative_bundle: str) -> dict[str, Any] | None:
    for receipt_path in sorted((root / "replication-records").glob("*.json")):
        receipt = read_json(receipt_path)
        if receipt.get("status") == "ACCEPTED" and receipt.get("retained_artifact_identity", {}).get("relative_path") == relative_bundle:
            return receipt
    return None


def command_history(args: argparse.Namespace) -> int:
    try:
        scope = parse_scope(args.operator)
        requested_target = canonicalize_url(args.target)
    except ValueError as exc:
        print(json.dumps({"status": "MALFORMED_QUERY", "detail": str(exc)}, sort_keys=True))
        return 1

    scope_results: list[dict[str, Any]] = []
    statements: list[dict[str, Any]] = []
    unavailable = 0
    for requested_id, root in scope:
        marker = root / "recovery" / "OFFLINE"
        if requested_id in args.unavailable or marker.exists() or not identity_path(root).exists():
            unavailable += 1
            scope_results.append({"operator": requested_id, "status": "UNAVAILABLE_OPERATOR", "detail": "Unavailable in declared local simulation scope."})
            continue
        identity = require_identity(root)
        if identity["operator_id"] != requested_id:
            scope_results.append({"operator": requested_id, "status": "UNAVAILABLE_OPERATOR", "detail": "Operator descriptor/identity does not match declared scope."})
            unavailable += 1
            continue
        scope_results.append({"operator": requested_id, "status": "QUERIED"})
        for manifest_path in sorted((root / "manifests").glob("*.json")):
            manifest = read_json(manifest_path)
            object_record = manifest.get("object", {})
            observed = object_record.get("observed_url")
            original = object_record.get("original_url")
            candidates = {value for value in (observed, original) if value}
            if not any(canonicalize_url(candidate) == requested_target for candidate in candidates):
                continue
            observation_id = manifest["observation_id"]
            relative_bundle = str(Path("evidence") / safe_name(observation_id))
            bundle = root / relative_bundle
            if not bundle.exists():
                verification = "MISSING_REPLICA"
            else:
                verification = verification_status(verify_bundle(bundle))
            receipt = receipt_for_bundle(root, relative_bundle)
            original_issuer = receipt["original_issuer"] if receipt else manifest["observer"]["observer_id"]
            replica = receipt["replica"] if receipt else identity["operator_id"]
            statements.append(
                {
                    "observation_id": observation_id,
                    "issuer": manifest["observer"]["observer_id"],
                    "capture_time": manifest["capture"]["captured_at"],
                    "artifact_digest": manifest["content"]["archive_hash"],
                    "verification_status": verification,
                    "evidence_reference": f"{requested_id}:{relative_bundle}",
                    "custody": {"operator": requested_id, "original_issuer": original_issuer, "replica": replica},
                }
            )

    verified = [statement for statement in statements if statement["verification_status"] == "VERIFIED"]
    distinct_digests = {statement["artifact_digest"] for statement in verified}
    if not statements:
        if unavailable == len(scope):
            status = "UNAVAILABLE_OPERATOR"
        elif unavailable:
            status = "PARTIAL_SCOPE"
        else:
            status = "NO_MATCH_IN_DECLARED_SCOPE"
    elif len(distinct_digests) > 1:
        status = "CONFLICT"
    elif unavailable or not verified:
        status = "PARTIAL_SCOPE"
    else:
        status = "VERIFIED"
    result = {
        "query_time": utc_now(),
        "target": requested_target,
        "declared_scope": [operator_id for operator_id, _ in scope],
        "scope_results": scope_results,
        "status": status,
        "statements": sorted(statements, key=lambda statement: (statement["capture_time"], statement["issuer"], statement["custody"]["operator"])),
    }
    if args.output:
        stable_write(args.output.resolve(), result)
    print(json.dumps(result, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OIN local network-demo operator commands")
    subcommands = parser.add_subparsers(dest="command", required=True)

    initialize = subcommands.add_parser("init", help="Create one isolated local operator identity and descriptor")
    initialize.add_argument("operator_root", type=Path)
    initialize.add_argument("--operator-id", required=True)
    initialize.add_argument("--descriptor-revision", type=int, default=1)
    initialize.add_argument("--force", action="store_true", help="Intentionally rotate an existing local demo key")
    initialize.set_defaults(handler=command_init)

    capture = subcommands.add_parser("capture", help="Capture a public HTTP(S) URL into a signed WARC/WACZ bundle")
    capture.add_argument("operator_root", type=Path)
    capture.add_argument("url")
    capture.add_argument("--archive-format", choices=("wacz", "warc"), default="wacz")
    capture.add_argument("--timeout-seconds", type=float, default=30.0)
    capture.set_defaults(handler=command_capture)

    verify = subcommands.add_parser("verify", help="Verify an offline bundle with no Operator service dependency")
    verify.add_argument("bundle", type=Path)
    verify.set_defaults(handler=command_verify)

    export = subcommands.add_parser("export", help="Create a portable signed ZIP containing one offline verification bundle")
    export.add_argument("operator_root", type=Path)
    export.add_argument("observation_id")
    export.add_argument("--output", type=Path)
    export.set_defaults(handler=command_export)

    importer = subcommands.add_parser("import", help="Verify a foreign export before retaining a replica and writing a receipt")
    importer.add_argument("operator_root", type=Path)
    importer.add_argument("export", type=Path)
    importer.set_defaults(handler=command_import)

    recovery = subcommands.add_parser("recover", help="Restore an Operator custody replica from a verified foreign export")
    recovery.add_argument("operator_root", type=Path)
    recovery.add_argument("export", type=Path)
    recovery.set_defaults(handler=command_recover)

    availability = subcommands.add_parser("availability", help="Set a local simulation Operator endpoint online or offline")
    availability.add_argument("operator_root", type=Path)
    availability.add_argument("state", choices=("online", "offline"))
    availability.set_defaults(handler=command_set_availability)

    history = subcommands.add_parser("history", help="Query a bounded scope of local Operator custody stores")
    history.add_argument("target")
    history.add_argument("--operator", action="append", required=True, help="OPERATOR_ID=PATH; repeat for every declared scope member")
    history.add_argument("--unavailable", action="append", default=[], help="Declared operator ID unavailable for this query")
    history.add_argument("--output", type=Path)
    history.set_defaults(handler=command_history)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
