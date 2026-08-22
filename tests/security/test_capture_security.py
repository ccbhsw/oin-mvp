from __future__ import annotations

import socket

import pytest

from oin.capture.http_capture import CaptureSafetyError, validate_capture_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.8/",
        "http://[::1]/",
        "file:///etc/passwd",
        "ftp://example.org/resource",
    ],
)
def test_capture_rejects_non_public_or_non_http_urls(url: str) -> None:
    with pytest.raises(CaptureSafetyError):
        validate_capture_url(url)


def test_capture_rejects_hostname_resolving_to_private_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.9", 443))],
    )
    with pytest.raises(CaptureSafetyError, match="non-public"):
        validate_capture_url("https://rebind-test.example/")
