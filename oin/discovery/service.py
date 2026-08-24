"""Configuration-backed helpers for the reversible Discovery API prototype."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .descriptor import OperatorDescriptor

DEFAULT_DESCRIPTOR_TTL_SECONDS = 86_400
MIN_DESCRIPTOR_TTL_SECONDS = 300
MAX_DESCRIPTOR_TTL_SECONDS = 604_800
DEFAULT_CAPABILITIES = ("capture", "replication", "verification")


class DiscoveryConfigurationError(ValueError):
    """Raised when an operator has not explicitly configured Discovery metadata."""


def build_local_descriptor(
    private_key: Ed25519PrivateKey,
    *,
    endpoints: list[str],
    region: str,
    capabilities: list[str],
    protocol_version: str,
    ttl_seconds: int = DEFAULT_DESCRIPTOR_TTL_SECONDS,
    now: datetime | None = None,
) -> OperatorDescriptor:
    """Build and sign one short-lived operator descriptor from explicit metadata."""
    if not endpoints:
        raise DiscoveryConfigurationError("OIN_DISCOVERY_ENDPOINTS must contain at least one public endpoint")
    if not MIN_DESCRIPTOR_TTL_SECONDS <= ttl_seconds <= MAX_DESCRIPTOR_TTL_SECONDS:
        raise DiscoveryConfigurationError(
            f"descriptor TTL must be between {MIN_DESCRIPTOR_TTL_SECONDS} and {MAX_DESCRIPTOR_TTL_SECONDS} seconds"
        )

    current = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()
    descriptor = OperatorDescriptor(
        operator_id=OperatorDescriptor.operator_id_for_public_key(public_key),
        public_key=public_key,
        endpoints=endpoints,
        capabilities=capabilities,
        region=region,
        protocol_version=protocol_version,
        updated_at=current,
        expires_at=current + timedelta(seconds=ttl_seconds),
    )
    descriptor.sign(private_key)
    return descriptor


def build_local_descriptor_from_environment(private_key: Ed25519PrivateKey) -> OperatorDescriptor:
    """Build a descriptor only when all operator-facing metadata is explicitly configured."""
    endpoints = [
        value.strip()
        for value in os.getenv("OIN_DISCOVERY_ENDPOINTS", "").split(",")
        if value.strip()
    ]
    capabilities = [
        value.strip()
        for value in os.getenv("OIN_DISCOVERY_CAPABILITIES", ",".join(DEFAULT_CAPABILITIES)).split(",")
        if value.strip()
    ]
    try:
        ttl_seconds = int(os.getenv("OIN_DISCOVERY_DESCRIPTOR_TTL_SECONDS", str(DEFAULT_DESCRIPTOR_TTL_SECONDS)))
    except ValueError as exc:
        raise DiscoveryConfigurationError("OIN_DISCOVERY_DESCRIPTOR_TTL_SECONDS must be an integer") from exc

    return build_local_descriptor(
        private_key,
        endpoints=endpoints,
        region=os.getenv("OIN_DISCOVERY_REGION", "ZZ"),
        capabilities=capabilities,
        protocol_version=os.getenv("OIN_DISCOVERY_PROTOCOL_VERSION", "oin/0.1"),
        ttl_seconds=ttl_seconds,
    )


__all__ = [
    "DEFAULT_DESCRIPTOR_TTL_SECONDS",
    "DiscoveryConfigurationError",
    "build_local_descriptor",
    "build_local_descriptor_from_environment",
]
