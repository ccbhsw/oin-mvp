"""Observer identity and Ed25519 signing primitives."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from oin.protocol.core import b64decode, b64encode, canonical_json, observer_id, utc_now


def generate_keypair() -> tuple[Ed25519PrivateKey, dict[str, Any]]:
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    public_doc = {
        "observer_id": observer_id(public_raw),
        "public_key": b64encode(public_raw),
        "key_algorithm": "Ed25519",
        "created_at": utc_now(),
    }
    return private_key, public_doc


def write_keypair(directory: str | Path, operator_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    private_key, public_doc = generate_keypair()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    private_path = directory / "observer-private.pem"
    private_path.write_bytes(private_bytes)
    os.chmod(private_path, 0o600)
    public_doc["operator_metadata"] = operator_metadata or {}
    (directory / "observer-public.json").write_text(json.dumps(public_doc, indent=2, sort_keys=True) + "\n")
    return public_doc


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("expected an Ed25519 private key")
    return key


def public_document(private_key: Ed25519PrivateKey, *, created_at: str | None = None) -> dict[str, str]:
    raw = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "observer_id": observer_id(raw),
        "public_key": b64encode(raw),
        "key_algorithm": "Ed25519",
        "created_at": created_at or utc_now(),
    }


def sign_json(private_key: Ed25519PrivateKey, payload: dict[str, Any]) -> str:
    return b64encode(private_key.sign(canonical_json(payload)))


def verify_json(public_key_b64: str, payload: dict[str, Any], signature_b64: str) -> bool:
    try:
        public_key = Ed25519PublicKey.from_public_bytes(b64decode(public_key_b64))
        public_key.verify(b64decode(signature_b64), canonical_json(payload))
        return True
    except Exception:
        return False
