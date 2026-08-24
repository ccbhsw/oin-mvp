import base64
import hashlib
import json
import re
from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

PROTOCOL_VERSION = "1.0"

def b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")

def b64decode(data: str) -> bytes:
    return base64.b64decode(data)

def canonical_json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_prefixed(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"

def artifact_ref(hash_str: str) -> str:
    return f"oin:artifact:{hash_str}"

def canonicalize_url(url: str) -> str:
    return url.split('?')[0].split('#')[0].lower().rstrip('/')

def object_id(canonical_url: str, resource_type: str) -> str:
    identity = f"{canonical_url}|{resource_type}".encode("utf-8")
    return f"oin:object:sha256:{hashlib.sha256(identity).hexdigest()}"

def observation_id(manifest: dict) -> str:
    payload = canonical_json(manifest)
    return f"oin:observation:sha256:{hashlib.sha256(payload).hexdigest()}"

def observer_id(public_key_raw: bytes) -> str:
    return f"oin:observer:sha256:{hashlib.sha256(public_key_raw).hexdigest()}"

def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
