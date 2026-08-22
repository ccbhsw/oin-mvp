"""HTTP capture for the MVP. Browsertrix/Playwright are pluggable future capture engines."""

from __future__ import annotations

import io
import ipaddress
import json
import socket
import uuid
import zipfile
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from oin.protocol.core import canonical_json, sha256_prefixed, utc_now

DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 5


class CaptureSafetyError(ValueError):
    """Raised before a capture could reach a disallowed network target."""


@dataclass
class CaptureResult:
    requested_url: str
    observed_url: str
    captured_at: str
    http_status: int
    http_headers: dict[str, str]
    redirect_chain: list[str]
    body: bytes
    content_type: str
    warc: bytes
    wacz: bytes


def _http_message(status: int, headers: dict[str, str], body: bytes) -> bytes:
    lines = [f"HTTP/1.1 {status}"] + [f"{k}: {v}" for k, v in sorted(headers.items(), key=lambda item: item[0].lower())]
    return ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8") + body


def _warc_record(record_type: str, target_url: str, date: str, content: bytes, content_type: str) -> bytes:
    record_id = f"urn:uuid:{uuid.uuid4()}"
    headers = [
        "WARC/1.1",
        f"WARC-Type: {record_type}",
        f"WARC-Record-ID: <{record_id}>",
        f"WARC-Date: {date}",
        f"WARC-Target-URI: {target_url}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(content)}",
        "",
        "",
    ]
    return "\r\n".join(headers).encode("utf-8") + content + b"\r\n\r\n"


def build_warc(url: str, captured_at: str, status: int, headers: dict[str, str], body: bytes) -> bytes:
    warcinfo = {"software": "oin-mvp/0.1", "format": "WARC File Format 1.1", "created": captured_at}
    info = _warc_record("warcinfo", url, captured_at, canonical_json(warcinfo), "application/json")
    request = _warc_record("request", url, captured_at, f"GET {url} HTTP/1.1\r\n\r\n".encode(), "application/http; msgtype=request")
    response = _warc_record("response", url, captured_at, _http_message(status, headers, body), "application/http; msgtype=response")
    return info + request + response


def response_body_from_archive(archive: bytes, archive_format: str) -> bytes:
    """Extract the first WARC response payload from an OIN MVP WARC/WACZ archive."""
    if archive_format == "wacz":
        with zipfile.ZipFile(io.BytesIO(archive), "r") as package:
            warc = package.read("archive/data.warc")
    elif archive_format == "warc":
        warc = archive
    else:
        raise ValueError("archive_format must be warc or wacz")
    cursor = 0
    while True:
        record_start = warc.find(b"WARC/1.1\r\n", cursor)
        if record_start < 0:
            raise ValueError("WARC response record not found")
        header_end = warc.find(b"\r\n\r\n", record_start)
        if header_end < 0:
            raise ValueError("malformed WARC header")
        headers = warc[record_start:header_end].decode("utf-8", errors="strict")
        content_length = next(
            int(line.split(":", 1)[1].strip())
            for line in headers.split("\r\n")
            if line.lower().startswith("content-length:")
        )
        block_start = header_end + 4
        block = warc[block_start:block_start + content_length]
        if len(block) != content_length:
            raise ValueError("truncated WARC content block")
        if "WARC-Type: response" in headers:
            message_end = block.find(b"\r\n\r\n")
            if message_end < 0:
                raise ValueError("malformed embedded HTTP response")
            return block[message_end + 4:]
        cursor = block_start + content_length + 4


def build_wacz(warc: bytes, url: str, captured_at: str) -> bytes:
    """Create a minimal WACZ 1.1-compatible package with WARC and file-level fixity."""
    pages = json.dumps({"format": "json-pages-1.0", "id": "pages", "title": "OIN Capture"}) + "\n"
    pages += json.dumps({"id": sha256_prefixed(warc)[7:17], "url": url, "ts": captured_at}) + "\n"
    datapackage = {
        "profile": "data-package",
        "wacz_version": "1.1.1",
        "title": "OIN capture",
        "created": captured_at,
        "mainPageUrl": url,
        "mainPageDate": captured_at,
        "software": "oin-mvp/0.1",
        "resources": [
            {"name": "data.warc", "path": "archive/data.warc", "hash": sha256_prefixed(warc), "bytes": len(warc)},
            {"name": "pages.jsonl", "path": "pages/pages.jsonl", "hash": sha256_prefixed(pages.encode()), "bytes": len(pages.encode())},
        ],
    }
    datapackage_bytes = canonical_json(datapackage)
    digest = canonical_json({"path": "datapackage.json", "hash": sha256_prefixed(datapackage_bytes)})
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("archive/data.warc", warc, compress_type=zipfile.ZIP_STORED)
        zf.writestr("pages/pages.jsonl", pages)
        zf.writestr("datapackage.json", datapackage_bytes)
        zf.writestr("datapackage-digest.json", digest)
    return output.getvalue()


def _is_public_ip(address: str) -> bool:
    return ipaddress.ip_address(address).is_global


def validate_capture_url(url: str) -> str:
    """Allow only HTTP(S) URLs that resolve exclusively to globally routable addresses."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise CaptureSafetyError("capture URL must use http or https")
    if not parsed.hostname or parsed.username or parsed.password:
        raise CaptureSafetyError("capture URL must contain a host and no userinfo")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, ValueError) as exc:
        raise CaptureSafetyError(f"capture host cannot be resolved safely: {parsed.hostname}") from exc
    resolved = {entry[4][0] for entry in addresses}
    if not resolved or any(not _is_public_ip(address) for address in resolved):
        raise CaptureSafetyError("capture host resolves to a non-public address")
    return url


def validate_replication_peer_url(
    peer_url: str,
    *,
    allow_private: bool = False,
    allowed_private_hosts: set[str] | None = None,
) -> str:
    """Allow public HTTP(S) peers by default; private peers need explicit host allowlisting."""
    try:
        return validate_capture_url(peer_url).rstrip("/")
    except CaptureSafetyError:
        parsed = urlsplit(peer_url)
        if (
            allow_private
            and parsed.scheme in {"http", "https"}
            and parsed.hostname
            and parsed.hostname.lower() in (allowed_private_hosts or set())
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
        ):
            return peer_url.rstrip("/")
        raise


def _read_limited(response: httpx.Response, max_response_bytes: int) -> bytes:
    declared = response.headers.get("content-length")
    if declared:
        try:
            if int(declared) > max_response_bytes:
                raise CaptureSafetyError("response exceeds configured maximum size")
        except ValueError:
            pass
    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > max_response_bytes:
            raise CaptureSafetyError("response exceeds configured maximum size")
    return bytes(body)


def capture_url(
    url: str,
    *,
    timeout_seconds: float = 30.0,
    user_agent: str = "OIN-Observer/0.1",
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
) -> CaptureResult:
    """Capture a public HTTP(S) resource, revalidating every redirect target before connection."""
    requested_url = validate_capture_url(url)
    captured_at = utc_now()
    redirect_chain: list[str] = []
    current_url = requested_url
    with httpx.Client(follow_redirects=False, timeout=timeout_seconds, headers={"User-Agent": user_agent}) as client:
        for _ in range(max_redirects + 1):
            validate_capture_url(current_url)
            with client.stream("GET", current_url) as response:
                location = response.headers.get("location")
                if response.status_code in {301, 302, 303, 307, 308} and location:
                    redirect_chain.append(str(response.url))
                    current_url = validate_capture_url(urljoin(str(response.url), location))
                    continue
                body = _read_limited(response, max_response_bytes)
                headers = {key.lower(): value for key, value in response.headers.items()}
                observed_url = str(response.url)
                redirect_chain.append(observed_url)
                warc = build_warc(observed_url, captured_at, response.status_code, headers, body)
                return CaptureResult(
                    requested_url=requested_url,
                    observed_url=observed_url,
                    captured_at=captured_at,
                    http_status=response.status_code,
                    http_headers=headers,
                    redirect_chain=redirect_chain,
                    body=body,
                    content_type=headers.get("content-type", "application/octet-stream"),
                    warc=warc,
                    wacz=build_wacz(warc, observed_url, captured_at),
                )
    raise CaptureSafetyError(f"redirect limit exceeded ({max_redirects})")
