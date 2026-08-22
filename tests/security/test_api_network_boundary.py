from __future__ import annotations

import stat
from pathlib import Path

import pytest

from oin.capture.http_capture import CaptureSafetyError, validate_replication_peer_url
from oin.identity.keys import write_keypair


def test_keypair_private_key_is_owner_only(tmp_path: Path) -> None:
    write_keypair(tmp_path)
    mode = stat.S_IMODE((tmp_path / "observer-private.pem").stat().st_mode)
    assert mode == 0o600


def test_replication_peer_rejects_private_addresses_by_default() -> None:
    with pytest.raises(CaptureSafetyError):
        validate_replication_peer_url("http://127.0.0.1:8000")


def test_private_replication_peer_requires_explicit_development_opt_in_and_host_allowlist() -> None:
    assert (
        validate_replication_peer_url(
            "http://observer-a:8000",
            allow_private=True,
            allowed_private_hosts={"observer-a"},
        )
        == "http://observer-a:8000"
    )
    with pytest.raises(CaptureSafetyError):
        validate_replication_peer_url(
            "http://169.254.169.254/latest/meta-data/",
            allow_private=True,
            allowed_private_hosts={"observer-a"},
        )


def test_private_replication_peer_opt_in_still_rejects_userinfo_and_queries() -> None:
    with pytest.raises(CaptureSafetyError):
        validate_replication_peer_url(
            "http://user:password@observer-a:8000",
            allow_private=True,
            allowed_private_hosts={"observer-a"},
        )
    with pytest.raises(CaptureSafetyError):
        validate_replication_peer_url(
            "http://observer-a:8000/?unexpected=true",
            allow_private=True,
            allowed_private_hosts={"observer-a"},
        )
