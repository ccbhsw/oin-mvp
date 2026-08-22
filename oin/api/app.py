"""FastAPI Observer Node for the OIN MVP."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from oin.api.repository import IndependenceProfile, Observer, Repository
from oin.capture.http_capture import (
    CaptureSafetyError,
    capture_url,
    validate_capture_url,
    validate_replication_peer_url,
)
from oin.discovery import BootstrapRegistry
from oin.discovery.audit import DiscoveryAuditLog
from oin.discovery.bootstrap import MAX_BUNDLE_BYTES
from oin.discovery.service import DiscoveryConfigurationError, build_local_descriptor_from_environment
from oin.identity.keys import load_private_key, write_keypair
from oin.observation.service import build_observation, verify_archive_binding, verify_manifest
from oin.storage.backends import FileStorage, S3Storage
from oin.timestamp.rfc3161 import local_declaration, obtain_rfc3161_token
from oin.transparency.merkle import MerkleLog, verify_proof

DATA_DIR = Path(os.getenv("OIN_DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("OIN_DATABASE_URL", f"sqlite:///{DATA_DIR / 'oin.db'}")
NODE_NAME = os.getenv("OIN_NODE_NAME", "observer-local")
PRIVATE_KEY_PATH = Path(os.getenv("OIN_PRIVATE_KEY_PATH", DATA_DIR / "keys" / "observer-private.pem"))
DISCOVERY_BOOTSTRAP_PATH = Path(
    os.getenv("OIN_DISCOVERY_BOOTSTRAP_PATH", DATA_DIR / "discovery" / "bootstrap.json")
)
DISCOVERY_AUDIT_PATH = Path(
    os.getenv("OIN_DISCOVERY_AUDIT_PATH", DATA_DIR / "discovery" / "bootstrap-audit.jsonl")
)

repo = Repository(DATABASE_URL)
repo.create_schema()
STORAGE_BACKEND_NAME = os.getenv("OIN_STORAGE_BACKEND", "filesystem")
if STORAGE_BACKEND_NAME == "s3":
    storage = S3Storage(
        os.environ["OIN_S3_BUCKET"],
        endpoint_url=os.getenv("OIN_S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
elif STORAGE_BACKEND_NAME == "filesystem":
    storage = FileStorage(DATA_DIR / "artifacts")
else:
    raise RuntimeError("OIN_STORAGE_BACKEND must be filesystem or s3")
log = MerkleLog(DATA_DIR / "transparency", log_id=f"oin-log-{NODE_NAME}")


def observer_key():
    if not PRIVATE_KEY_PATH.exists():
        write_keypair(PRIVATE_KEY_PATH.parent, {"node_name": NODE_NAME})
    return load_private_key(PRIVATE_KEY_PATH)


def local_discovery_descriptor() -> dict[str, Any]:
    """Return this node's signed descriptor from explicit operator configuration."""
    try:
        return build_local_descriptor_from_environment(observer_key()).model_dump(mode="json")
    except DiscoveryConfigurationError as exc:
        raise HTTPException(status_code=503, detail=f"discovery descriptor unavailable: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="discovery descriptor configuration is invalid") from exc


def discovery_peers() -> dict[str, Any]:
    """Return valid Bootstrap records and audit a newly observed local Bundle revision."""
    registry = BootstrapRegistry()
    bundle_bytes: bytes | None = None
    report = None
    try:
        key = observer_key()
        registry.add_descriptor(build_local_descriptor_from_environment(key))
        if DISCOVERY_BOOTSTRAP_PATH.exists():
            if DISCOVERY_BOOTSTRAP_PATH.stat().st_size > MAX_BUNDLE_BYTES:
                raise ValueError("bootstrap bundle exceeds the configured maximum size")
            bundle_bytes = DISCOVERY_BOOTSTRAP_PATH.read_bytes()
            report = registry.import_bundle_report(bundle_bytes)
        registry.remove_expired()
        if bundle_bytes is not None and report is not None:
            DiscoveryAuditLog(DISCOVERY_AUDIT_PATH).record_bootstrap_load(
                key,
                bundle_bytes=bundle_bytes,
                accepted_count=report.accepted_count,
                rejected_count=report.rejected_count,
                active_count=len(registry.get_active_operators()),
            )
    except DiscoveryConfigurationError as exc:
        raise HTTPException(status_code=503, detail=f"discovery peers unavailable: {exc}") from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="discovery bootstrap configuration is invalid") from exc

    return {
        "version": "1",
        "descriptors": [item.model_dump(mode="json") for item in registry.get_active_operators()],
    }


def archive_key(manifest: dict[str, Any]) -> str:
    archive_hash = manifest["content"]["archive_hash"].split(":", 1)[1]
    return f"sha256/{archive_hash[:2]}/{archive_hash}.{manifest['content']['archive_format']}"


def ingest(
    manifest: dict[str, Any],
    archive: bytes,
    source: str = "local",
    timestamp_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify first, then persist archive and local independent log entry. Never replaces a conflicting observation."""
    verification = verify_manifest(manifest)
    if not verification["valid"]:
        raise HTTPException(status_code=422, detail={"reason": "invalid manifest", "verification": verification})
    binding = verify_archive_binding(manifest, archive)
    if not all(binding.values()):
        raise HTTPException(status_code=422, detail={"reason": "archive/content binding invalid", "checks": binding})
    existing = repo.observation(manifest["observation_id"])
    if existing:
        return {"status": "already_present", "observation_id": manifest["observation_id"], "proof": repo.log_proof(manifest["observation_id"])}
    key = archive_key(manifest)
    storage.put(key, archive)
    log.append(manifest)
    proof = log.proof(manifest["observation_id"])
    assert proof is not None
    repo.save_observation(
        manifest,
        storage_backend=STORAGE_BACKEND_NAME,
        storage_locator=key,
        log_proof=proof,
        timestamp_evidence=timestamp_evidence,
    )
    stored = repo.observation(manifest["observation_id"])
    assert stored is not None
    conflicts = repo.record_conflicts(manifest["object"]["object_id"], stored)
    return {
        "status": "created",
        "observation_id": manifest["observation_id"],
        "source": source,
        "proof": proof,
        "conflicts_created": [item.classification for item in conflicts],
    }


class CaptureRequest(BaseModel):
    url: str
    archive_format: str = Field(default="wacz", pattern="^(warc|wacz)$")
    resource_type: str = Field(default="html", pattern="^(html|document|feed|other)$")
    tsa_url: str | None = None


class ReplicationEnvelope(BaseModel):
    manifest: dict[str, Any]
    archive_b64: str
    source_node: str | None = None
    source_proof: dict[str, Any] | None = None
    timestamp_evidence: dict[str, Any] | None = None


class PullRequest(BaseModel):
    peer_url: str
    observation_ids: list[str] = Field(default_factory=list)


class ObserverRegistration(BaseModel):
    observer_id: str
    public_key: str
    key_algorithm: str = "Ed25519"
    created_at: str
    operator_metadata: dict[str, Any] = Field(default_factory=dict)
    independence_profile: dict[str, Any] | None = None


app = FastAPI(title="OIN MVP Observer Node", version="0.1.0", description="Signed, conflict-preserving observations of public information.")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "node": NODE_NAME}


@app.get("/v1/node")
def node_info() -> dict[str, Any]:
    key = observer_key()
    from oin.identity.keys import public_document
    return {"node_name": NODE_NAME, "observer": public_document(key), "log_id": log.log_id, "log_public_key": log.public_key_b64}


@app.get("/v1/discovery/descriptor")
def get_discovery_descriptor() -> dict[str, Any]:
    """Publish this operator's short-lived self-authenticating descriptor."""
    return local_discovery_descriptor()


@app.get("/v1/discovery/peers")
def get_discovery_peers() -> dict[str, Any]:
    """Publish a verifiable, replaceable static Bootstrap peer list."""
    return discovery_peers()


@app.post("/v1/captures", status_code=201)
def create_capture(request: CaptureRequest) -> dict[str, Any]:
    try:
        result = capture_url(request.url)
    except CaptureSafetyError as exc:
        raise HTTPException(status_code=422, detail=f"capture URL rejected: {exc}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"capture failed: {exc}") from exc
    manifest, archive = build_observation(
        result, observer_key(), archive_format=request.archive_format, resource_type=request.resource_type
    )
    evidence = local_declaration(manifest)
    if request.tsa_url:
        try:
            evidence = obtain_rfc3161_token(manifest, validate_capture_url(request.tsa_url))
        except Exception as exc:
            evidence["timestamp_error"] = str(exc)
    return {
        "manifest": manifest,
        "timestamp_evidence": evidence,
        **ingest(manifest, archive, source="capture", timestamp_evidence=evidence),
    }


@app.post("/v1/observations", status_code=201)
def create_observation(envelope: ReplicationEnvelope) -> dict[str, Any]:
    try:
        archive = base64.b64decode(envelope.archive_b64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="archive_b64 is invalid") from exc
    return ingest(
        envelope.manifest,
        archive,
        source=envelope.source_node or "external",
        timestamp_evidence=envelope.timestamp_evidence,
    )


@app.get("/v1/observations/{observation_id}")
def get_observation(observation_id: str) -> dict[str, Any]:
    observation = repo.observation(observation_id)
    if not observation:
        raise HTTPException(status_code=404, detail="observation not found")
    return observation.manifest


@app.get("/v1/observations/{observation_id}/raw")
def get_raw(observation_id: str) -> Response:
    observation, reference = repo.observation(observation_id), repo.storage_ref(observation_id)
    if not observation or not reference:
        raise HTTPException(status_code=404, detail="raw archive not found")
    media_type = observation.manifest["content"]["archive_media_type"]
    return Response(storage.get(reference.locator), media_type=media_type, headers={"Content-Disposition": f"attachment; filename=raw.{observation.archive_format}"})


@app.get("/v1/observations/{observation_id}/proof")
def get_proof(observation_id: str) -> dict[str, Any]:
    proof = repo.log_proof(observation_id)
    if not proof:
        raise HTTPException(status_code=404, detail="proof not found")
    return proof


@app.get("/v1/objects/{object_id}")
def get_object(object_id: str) -> dict[str, Any]:
    observations = repo.observations_for_object(object_id)
    if not observations:
        raise HTTPException(status_code=404, detail="object not found")
    first = observations[0].object
    return {"object_id": object_id, "canonical_url": first.canonical_url, "resource_type": first.resource_type, "observation_count": len(observations)}


@app.get("/v1/objects/{object_id}/observations")
def object_observations(object_id: str) -> list[dict[str, Any]]:
    return [item.manifest for item in repo.observations_for_object(object_id)]


@app.get("/v1/objects/{object_id}/history")
def object_history(object_id: str) -> dict[str, Any]:
    values = repo.observations_for_object(object_id)
    if not values:
        raise HTTPException(status_code=404, detail="object not found")
    return {"object_id": object_id, "history": [{"captured_at": item.captured_at, "observation_id": item.observation_id, "observer_id": item.observer_id, "raw_content_hash": item.raw_content_hash} for item in values]}


@app.get("/v1/objects/{object_id}/conflicts")
def object_conflicts(object_id: str) -> list[dict[str, Any]]:
    return [{"observation_a_id": row.observation_a_id, "observation_b_id": row.observation_b_id, "classification": row.classification, "is_conflict_candidate": row.is_conflict_candidate, "details": row.details} for row in repo.conflicts_for_object(object_id)]


@app.get("/v1/verify/{observation_id}")
def verify_observation(observation_id: str) -> dict[str, Any]:
    observation, reference, proof = repo.observation(observation_id), repo.storage_ref(observation_id), repo.log_proof(observation_id)
    if not observation or not reference:
        raise HTTPException(status_code=404, detail="observation not found")
    binding = verify_archive_binding(observation.manifest, storage.get(reference.locator))
    manifest_result = verify_manifest(observation.manifest)
    proof_valid = verify_proof(observation.manifest, proof) if proof else False
    return {
        "status": "VALID" if all(binding.values()) and manifest_result["valid"] and proof_valid else "INVALID",
        "archive_hash_valid": binding["archive_hash"],
        "raw_content_hash_valid": binding["raw_content_hash"],
        "raw_content_bytes_valid": binding["raw_content_bytes"],
        "manifest": manifest_result,
        "transparency_proof_valid": proof_valid,
    }


@app.post("/v1/observers", status_code=201)
def register_observer(request: ObserverRegistration) -> dict[str, str]:
    if request.key_algorithm != "Ed25519":
        raise HTTPException(status_code=422, detail="OIN MVP supports Ed25519 observer keys only")
    with repo.session_factory.begin() as session:
        if not session.get(Observer, request.observer_id):
            session.add(Observer(**request.model_dump(exclude={"independence_profile"})))
        if request.independence_profile:
            if not session.get(IndependenceProfile, request.observer_id):
                session.add(IndependenceProfile(observer_id=request.observer_id, profile=request.independence_profile))
    return {"status": "registered", "observer_id": request.observer_id}


@app.get("/v1/observers/{observer_id}")
def get_observer(observer_id: str) -> dict[str, Any]:
    with repo.session_factory() as session:
        observer = session.get(Observer, observer_id)
        if not observer:
            raise HTTPException(status_code=404, detail="observer not found")
        profile = session.get(IndependenceProfile, observer_id)
        return {"observer_id": observer.observer_id, "public_key": observer.public_key, "key_algorithm": observer.key_algorithm, "created_at": observer.created_at, "key_status": observer.key_status, "operator_metadata": observer.operator_metadata, "independence_profile": profile.profile if profile else None}


@app.get("/v1/replication/ids")
def replication_ids() -> dict[str, list[str]]:
    return {"observation_ids": repo.list_observation_ids()}


@app.get("/v1/replication/export/{observation_id}")
def replication_export(observation_id: str) -> dict[str, Any]:
    observation, reference = repo.observation(observation_id), repo.storage_ref(observation_id)
    if not observation or not reference:
        raise HTTPException(status_code=404, detail="observation not found")
    return {
        "manifest": observation.manifest,
        "archive_b64": base64.b64encode(storage.get(reference.locator)).decode("ascii"),
        "source_node": NODE_NAME,
        "source_proof": repo.log_proof(observation_id),
        "timestamp_evidence": repo.timestamp_evidence(observation_id),
    }


@app.post("/v1/replication/push", status_code=201)
def replication_push(envelope: ReplicationEnvelope) -> dict[str, Any]:
    return create_observation(envelope)


@app.post("/v1/replication/pull")
def replication_pull(request: PullRequest) -> dict[str, Any]:
    ids = request.observation_ids
    try:
        allowed_private_hosts = {
            host.strip().lower()
            for host in os.getenv("OIN_ALLOWED_PRIVATE_PEER_HOSTS", "").split(",")
            if host.strip()
        }
        peer = validate_replication_peer_url(
            request.peer_url,
            allow_private=os.getenv("OIN_ALLOW_PRIVATE_PEERS") == "1",
            allowed_private_hosts=allowed_private_hosts,
        )
        with httpx.Client(timeout=60.0) as client:
            if not ids:
                ids = client.get(f"{peer}/v1/replication/ids").raise_for_status().json()["observation_ids"]
            results = []
            for observation_id in ids:
                response = client.get(f"{peer}/v1/replication/export/{observation_id}")
                response.raise_for_status()
                payload = ReplicationEnvelope.model_validate(response.json())
                results.append(create_observation(payload))
    except CaptureSafetyError as exc:
        raise HTTPException(status_code=422, detail=f"replication peer rejected: {exc}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"replication pull failed: {exc}") from exc
    return {"peer_url": peer, "results": results}
