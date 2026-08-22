"""End-to-end and fault tests for the OIN local network demo.

These tests exercise local isolation and portable artifact boundaries.  They do
not claim that the temporary directories represent independent organizations.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PYTHON_OPERATOR = ROOT / "network-demo" / "tools" / "operator.py"
NODE_VERIFIER = ROOT / "network-demo" / "tools" / "node_verifier.mjs"
TARGET = "https://example.com"


def invoke(*arguments: str | Path, expected: int = 0) -> dict:
    result = subprocess.run(
        [sys.executable, str(PYTHON_OPERATOR), *map(str, arguments)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=90,
    )
    assert result.returncode == expected, result.stderr or result.stdout
    return json.loads(result.stdout.strip().splitlines()[-1])


def invoke_node(*arguments: str | Path, expected: int = 0) -> dict:
    result = subprocess.run(
        ["node", str(NODE_VERIFIER), *map(str, arguments)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=90,
    )
    assert result.returncode == expected, result.stderr or result.stdout
    return json.loads(result.stdout.strip().splitlines()[-1])


def initialize(root: Path, name: str) -> None:
    result = invoke("init", root, "--operator-id", f"did:oin-local:{name}")
    assert result["status"] == "INITIALIZED"


def capture(root: Path, url: str = TARGET, timeout: float | None = None, expected: int = 0) -> dict:
    arguments: list[str | Path] = ["capture", root, url, "--archive-format", "wacz"]
    if timeout is not None:
        arguments.extend(["--timeout-seconds", str(timeout)])
    return invoke(*arguments, expected=expected)


def bundle_from(root: Path, observation_id: str) -> Path:
    return root / "evidence" / observation_id.replace(":", "_")


def create_export(source_root: Path, observation_id: str, output: Path) -> dict:
    return invoke("export", source_root, observation_id, "--output", output)


def duplicate_zip(source: Path, destination: Path, mutator) -> None:
    with zipfile.ZipFile(source, "r") as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    mutator(files)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


@pytest.fixture()
def captured_a(tmp_path: Path) -> tuple[Path, dict]:
    operator_a = tmp_path / "operator-a"
    initialize(operator_a, "operator-a")
    result = capture(operator_a)
    assert result["status"] == "CAPTURED"
    assert result["http_status"] == 200
    assert result["verification"] == "VERIFIED"
    return operator_a, result


def test_real_http_capture_wacz_python_and_node_verify(captured_a: tuple[Path, dict]) -> None:
    operator_a, result = captured_a
    bundle = bundle_from(operator_a, result["observation_id"])
    assert (bundle / "raw.wacz").exists()
    assert invoke("verify", bundle)["status"] == "VERIFIED"
    assert invoke_node("verify-bundle", bundle)["status"] == "VERIFIED"


def test_a_to_b_to_c_recovery_conflict_and_cross_implementation(captured_a: tuple[Path, dict], tmp_path: Path) -> None:
    operator_a, capture_a = captured_a
    operator_b = tmp_path / "operator-b"
    operator_c = tmp_path / "operator-c"
    initialize(operator_b, "operator-b")
    export_a = tmp_path / "a-export.zip"
    assert create_export(operator_a, capture_a["observation_id"], export_a)["status"] == "EXPORTED"
    imported_b = invoke("import", operator_b, export_a)
    assert imported_b["status"] == "ACCEPTED"
    assert imported_b["original_issuer"] != json.loads((operator_b / "identity" / "operator.json").read_text())["observer_id"]

    export_b = tmp_path / "b-export.zip"
    assert create_export(operator_b, capture_a["observation_id"], export_b)["status"] == "EXPORTED"
    initialize(operator_c, "operator-c")
    assert invoke("import", operator_c, export_b)["status"] == "ACCEPTED"
    assert invoke_node("verify-export", export_b)["status"] == "VERIFIED"

    node_export = tmp_path / "node-created-c-export.zip"
    retained_c = bundle_from(operator_c, capture_a["observation_id"])
    node_result = invoke_node(
        "create-export",
        retained_c,
        operator_c / "descriptors" / "operator-descriptor.json",
        operator_c / "keys" / "observer-private.pem",
        operator_c / "keys" / "observer-public.json",
        node_export,
    )
    assert node_result["status"] == "VERIFIED"
    assert invoke("import", operator_b, node_export)["status"] == "ACCEPTED"

    lost = operator_a / "recovery" / "lost-primary-material"
    lost.mkdir(parents=True)
    for name in ("evidence", "manifests", "statements", "verification-results"):
        shutil.move(str(operator_a / name), lost / name)
        (operator_a / name).mkdir()
    assert not bundle_from(operator_a, capture_a["observation_id"]).exists()
    assert invoke("recover", operator_a, export_b)["status"] == "RECOVERED"
    assert invoke("verify", bundle_from(operator_a, capture_a["observation_id"]))["status"] == "VERIFIED"

    capture_c = capture(operator_c)
    assert capture_c["status"] == "CAPTURED"
    history = invoke(
        "history",
        TARGET,
        "--operator",
        f"did:oin-local:operator-a={operator_a}",
        "--operator",
        f"did:oin-local:operator-b={operator_b}",
        "--operator",
        f"did:oin-local:operator-c={operator_c}",
    )
    assert history["status"] == "CONFLICT"
    assert len(history["statements"]) >= 4


def test_tampered_evidence_is_rejected_before_retention(captured_a: tuple[Path, dict], tmp_path: Path) -> None:
    operator_a, captured = captured_a
    operator_b = tmp_path / "operator-b"
    initialize(operator_b, "operator-b")
    source = tmp_path / "source.zip"
    tampered = tmp_path / "tampered-evidence.zip"
    create_export(operator_a, captured["observation_id"], source)
    duplicate_zip(source, tampered, lambda files: files.__setitem__("bundle/raw.wacz", b"tampered"))
    result = invoke("import", operator_b, tampered, expected=1)
    assert result["status"] == "INVALID_BINDING"
    receipt = json.loads(Path(result["replication_record"]).read_text())
    assert receipt["status"] == "REJECTED"
    assert not any((operator_b / "evidence").iterdir())


def test_tampered_export_signature_is_rejected(captured_a: tuple[Path, dict], tmp_path: Path) -> None:
    operator_a, captured = captured_a
    operator_b = tmp_path / "operator-b"
    initialize(operator_b, "operator-b")
    source = tmp_path / "source.zip"
    tampered = tmp_path / "tampered-signature.zip"
    create_export(operator_a, captured["observation_id"], source)

    def alter_signature(files: dict[str, bytes]) -> None:
        signature = json.loads(files["export-signature.json"])
        signature["value"] = "AAAA"
        files["export-signature.json"] = json.dumps(signature, separators=(",", ":")).encode()

    duplicate_zip(source, tampered, alter_signature)
    assert invoke("import", operator_b, tampered, expected=1)["status"] == "INVALID_SIGNATURE"


def test_descriptor_change_is_rejected(captured_a: tuple[Path, dict], tmp_path: Path) -> None:
    operator_a, captured = captured_a
    operator_b = tmp_path / "operator-b"
    initialize(operator_b, "operator-b")
    source = tmp_path / "source.zip"
    altered = tmp_path / "altered-descriptor.zip"
    create_export(operator_a, captured["observation_id"], source)

    def alter_descriptor(files: dict[str, bytes]) -> None:
        descriptor = json.loads(files["operator-descriptor.json"])
        descriptor["descriptor_revision"] = 2
        files["operator-descriptor.json"] = json.dumps(descriptor, separators=(",", ":")).encode()

    duplicate_zip(source, altered, alter_descriptor)
    assert invoke("import", operator_b, altered, expected=1)["status"] == "INVALID_BINDING"


def test_missing_replica_and_scope_status(captured_a: tuple[Path, dict], tmp_path: Path) -> None:
    operator_a, captured = captured_a
    operator_b = tmp_path / "operator-b"
    initialize(operator_b, "operator-b")
    export = tmp_path / "source.zip"
    create_export(operator_a, captured["observation_id"], export)
    invoke("import", operator_b, export)
    shutil.rmtree(bundle_from(operator_b, captured["observation_id"]))
    history = invoke("history", TARGET, "--operator", f"did:oin-local:operator-b={operator_b}")
    assert history["status"] == "PARTIAL_SCOPE"
    assert history["statements"][0]["verification_status"] == "MISSING_REPLICA"


def test_unavailable_and_no_match_scope_states(captured_a: tuple[Path, dict], tmp_path: Path) -> None:
    operator_a, _ = captured_a
    assert invoke("availability", operator_a, "offline")["status"] == "OFFLINE"
    unavailable = invoke("history", TARGET, "--operator", f"did:oin-local:operator-a={operator_a}")
    assert unavailable["status"] == "UNAVAILABLE_OPERATOR"
    assert unavailable["scope_results"][0]["status"] == "UNAVAILABLE_OPERATOR"
    invoke("availability", operator_a, "online")
    no_match = invoke("history", "https://no-history.example", "--operator", f"did:oin-local:operator-a={operator_a}")
    assert no_match["status"] == "NO_MATCH_IN_DECLARED_SCOPE"


def test_http_404_and_timeout_are_machine_readable(tmp_path: Path) -> None:
    operator_a = tmp_path / "operator-a"
    initialize(operator_a, "operator-a")
    not_found = capture(operator_a, "https://example.com/oin-network-demo-definitely-missing")
    assert not_found["status"] == "CAPTURED"
    assert not_found["http_status"] == 404
    timeout = capture(operator_a, TARGET, timeout=0.000001, expected=1)
    assert timeout["status"] == "TIMEOUT"


def test_missing_export_reports_not_found(tmp_path: Path) -> None:
    operator_b = tmp_path / "operator-b"
    initialize(operator_b, "operator-b")
    result = invoke("import", operator_b, tmp_path / "missing.zip", expected=1)
    assert result["status"] == "NOT_FOUND"


def test_tampered_manifest_signature_fails_offline_verifiers(captured_a: tuple[Path, dict], tmp_path: Path) -> None:
    operator_a, captured = captured_a
    original = bundle_from(operator_a, captured["observation_id"])
    altered = tmp_path / "altered-bundle"
    shutil.copytree(original, altered)
    manifest = json.loads((altered / "observation.json").read_text())
    manifest["signature"]["value"] = "AAAA"
    (altered / "observation.json").write_text(json.dumps(manifest, separators=(",", ":")))
    assert invoke("verify", altered, expected=1)["status"] == "INVALID_SIGNATURE"
    assert invoke_node("verify-bundle", altered, expected=1)["status"] == "INVALID_SIGNATURE"


def test_malformed_export_is_rejected(tmp_path: Path) -> None:
    operator_b = tmp_path / "operator-b"
    initialize(operator_b, "operator-b")
    malformed = tmp_path / "malformed.zip"
    malformed.write_bytes(b"this is not a ZIP file")
    result = invoke("import", operator_b, malformed, expected=1)
    assert result["status"] == "MALFORMED_ARTIFACT"


def test_export_with_too_many_zip_members_is_rejected(tmp_path: Path) -> None:
    operator_b = tmp_path / "operator-b"
    initialize(operator_b, "operator-b")
    oversized = tmp_path / "too-many-members.zip"
    with zipfile.ZipFile(oversized, "w") as archive:
        for index in range(17):
            archive.writestr(f"member-{index}.txt", "x")
    result = invoke("import", operator_b, oversized, expected=1)
    assert result["status"] == "MALFORMED_ARTIFACT"
    assert not any((operator_b / "evidence").iterdir())
