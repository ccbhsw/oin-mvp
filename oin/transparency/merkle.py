"""CT-style binary Merkle tree and signed checkpoints for OIN transparency logs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from oin.identity.keys import sign_json, verify_json
from oin.protocol.core import b64encode, canonical_json, sha256_prefixed, utc_now


def _hash(value: bytes) -> bytes:
    return hashlib.sha256(value).digest()


def leaf_hash(entry: bytes) -> bytes:
    return _hash(b"\x00" + entry)


def node_hash(left: bytes, right: bytes) -> bytes:
    return _hash(b"\x01" + left + right)


def _split(size: int) -> int:
    return 1 << ((size - 1).bit_length() - 1)


def root(entries: list[bytes]) -> bytes:
    if not entries:
        return _hash(b"")
    if len(entries) == 1:
        return leaf_hash(entries[0])
    split = _split(len(entries))
    return node_hash(root(entries[:split]), root(entries[split:]))


def inclusion_path(index: int, entries: list[bytes]) -> list[bytes]:
    if index < 0 or index >= len(entries):
        raise IndexError("leaf index out of range")
    if len(entries) == 1:
        return []
    split = _split(len(entries))
    if index < split:
        return inclusion_path(index, entries[:split]) + [root(entries[split:])]
    return inclusion_path(index - split, entries[split:]) + [root(entries[:split])]


def verify_inclusion(index: int, tree_size: int, entry: bytes, path: list[bytes], expected_root: bytes) -> bool:
    """RFC 9162 §2.1.3.2 style audit-path verification."""
    if index < 0 or index >= tree_size:
        return False
    fn, sn, computed = index, tree_size - 1, leaf_hash(entry)
    for sibling in path:
        if sn == 0:
            return False
        if (fn & 1) or fn == sn:
            computed = node_hash(sibling, computed)
            if not (fn & 1):
                while fn and not (fn & 1):
                    fn >>= 1
                    sn >>= 1
        else:
            computed = node_hash(computed, sibling)
        fn >>= 1
        sn >>= 1
    return sn == 0 and computed == expected_root


class MerkleLog:
    """Local append-only log prototype. File retention and witness publication are deployment concerns."""

    def __init__(self, directory: str | Path, log_id: str = "oin-log-local") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.entries_path = self.directory / "entries.jsonl"
        self.key_path = self.directory / "log-private.pem"
        self.public_path = self.directory / "log-public.key"
        self.log_id = log_id
        self.private_key = self._load_or_create_key()
        self.public_key_b64 = b64encode(
            self.private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        )
        self.public_path.write_text(self.public_key_b64 + "\n")

    def _load_or_create_key(self) -> Ed25519PrivateKey:
        if self.key_path.exists():
            key = serialization.load_pem_private_key(self.key_path.read_bytes(), password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise TypeError("transparency log key must be Ed25519")
            return key
        key = Ed25519PrivateKey.generate()
        self.key_path.write_bytes(
            key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        )
        return key

    def _entries(self) -> list[dict[str, Any]]:
        if not self.entries_path.exists():
            return []
        return [json.loads(line) for line in self.entries_path.read_text().splitlines() if line.strip()]

    @staticmethod
    def entry_bytes(entry: dict[str, Any]) -> bytes:
        return canonical_json({"observation_id": entry["observation_id"], "manifest_hash": entry["manifest_hash"]})

    def checkpoint(self, entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        entries = self._entries() if entries is None else entries
        checkpoint = {
            "log_id": self.log_id,
            "log_key_algorithm": "Ed25519",
            "log_public_key": self.public_key_b64,
            "tree_size": len(entries),
            "root_hash": f"sha256:{root([self.entry_bytes(entry) for entry in entries]).hex()}",
            "issued_at": utc_now(),
        }
        checkpoint["signature"] = sign_json(self.private_key, checkpoint)
        return checkpoint

    def append(self, manifest: dict[str, Any]) -> dict[str, Any]:
        entries = self._entries()
        manifest_hash = sha256_prefixed(canonical_json(manifest))
        entry = {
            "log_id": self.log_id,
            "leaf_index": len(entries),
            "observation_id": manifest["observation_id"],
            "manifest_hash": manifest_hash,
            "integrated_at": utc_now(),
        }
        entries.append(entry)
        with self.entries_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return {"entry": entry, "checkpoint": self.checkpoint(entries)}

    def proof(self, observation_id: str) -> dict[str, Any] | None:
        entries = self._entries()
        for entry in entries:
            if entry["observation_id"] == observation_id:
                values = [self.entry_bytes(value) for value in entries]
                checkpoint = self.checkpoint(entries)
                return {
                    "entry": entry,
                    "inclusion_path": [f"sha256:{value.hex()}" for value in inclusion_path(entry["leaf_index"], values)],
                    "checkpoint": checkpoint,
                }
        return None


def verify_proof(manifest: dict[str, Any], proof: dict[str, Any]) -> bool:
    try:
        entry = proof["entry"]
        checkpoint = proof["checkpoint"]
        if entry["observation_id"] != manifest["observation_id"]:
            return False
        if entry["manifest_hash"] != sha256_prefixed(canonical_json(manifest)):
            return False
        unsigned_checkpoint = dict(checkpoint)
        signature = unsigned_checkpoint.pop("signature")
        if not verify_json(checkpoint["log_public_key"], unsigned_checkpoint, signature):
            return False
        path = [bytes.fromhex(item.split(":", 1)[1]) for item in proof["inclusion_path"]]
        expected = bytes.fromhex(checkpoint["root_hash"].split(":", 1)[1])
        return verify_inclusion(
            entry["leaf_index"], checkpoint["tree_size"], MerkleLog.entry_bytes(entry), path, expected
        )
    except Exception:
        return False
