"""Storage adapters. Observations reference immutable SHA-256 artifacts, not provider-specific paths."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    def put(self, key: str, value: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...
    def list(self, prefix: str = "") -> list[str]: ...
    def verify(self, key: str, expected_sha256: str) -> bool: ...


class FileStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        key = key.lstrip("/")
        if ".." in Path(key).parts:
            raise ValueError("invalid storage key")
        return self.root / key

    def put(self, key: str, value: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def list(self, prefix: str = "") -> list[str]:
        base = self._path(prefix)
        if not base.exists():
            return []
        return sorted(str(item.relative_to(self.root)) for item in base.rglob("*") if item.is_file())

    def verify(self, key: str, expected_sha256: str) -> bool:
        value = self.get(key)
        return hashlib.sha256(value).hexdigest() == expected_sha256.removeprefix("sha256:")


class S3Storage:
    """Thin S3-compatible adapter. Instantiate only when boto3 is installed."""

    def __init__(self, bucket: str, endpoint_url: str | None = None, **client_kwargs: str) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("install oin-mvp[s3] to use S3Storage") from exc
        self.bucket = bucket
        self.client = boto3.client("s3", endpoint_url=endpoint_url, **client_kwargs)

    def put(self, key: str, value: bytes) -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=value)
        return key

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def list(self, prefix: str = "") -> list[str]:
        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [entry["Key"] for entry in response.get("Contents", [])]

    def verify(self, key: str, expected_sha256: str) -> bool:
        return hashlib.sha256(self.get(key)).hexdigest() == expected_sha256.removeprefix("sha256:")
