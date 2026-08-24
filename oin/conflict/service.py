"""Conflict identity for observations.

URL captures keep using object_id(canonical_url, resource_type).
Text and file captures use canonical_id when the caller supplies one; otherwise
each capture is a new object and does not join an existing conflict set.
"""

from __future__ import annotations

import uuid

from oin.protocol.core import canonicalize_url, object_id


def object_identity(
    *,
    canonical_url: str | None = None,
    canonical_id: str | None = None,
    resource_type: str = "other",
) -> str:
    identifier = (canonical_id or "").strip()
    if identifier:
        return object_id(f"canonical-id:{identifier}", resource_type)
    url = (canonical_url or "").strip()
    if url:
        return object_id(canonicalize_url(url), resource_type)
    return object_id(f"independent:{uuid.uuid4()}", resource_type)
