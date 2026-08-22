from __future__ import annotations

import hashlib

import pytest

from oin.storage.backends import FileStorage


def test_filestorage_write_read_duplicate_and_checksum(tmp_path) -> None:
    storage = FileStorage(tmp_path / "artifacts")
    key = "sha256/ab/example.wacz"
    original = b"archive-v1"
    digest = "sha256:" + hashlib.sha256(original).hexdigest()

    assert storage.put(key, original) == key
    assert storage.get(key) == original
    assert storage.verify(key, digest) is True
    assert storage.put(key, original) == key
    assert storage.get(key) == original
    assert storage.list("sha256") == [key]


def test_filestorage_detects_missing_and_corrupted_object(tmp_path) -> None:
    storage = FileStorage(tmp_path / "artifacts")
    key = "sha256/cd/example.wacz"
    original = b"archive-v1"
    digest = "sha256:" + hashlib.sha256(original).hexdigest()
    storage.put(key, original)
    path = tmp_path / "artifacts" / key
    path.write_bytes(b"archive-corrupted")
    assert storage.verify(key, digest) is False
    storage.delete(key)
    assert storage.exists(key) is False
    with pytest.raises(FileNotFoundError):
        storage.get(key)
