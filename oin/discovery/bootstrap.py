"""A lightweight signed-descriptor Bootstrap registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
try:
    from datetime import UTC
except ImportError:
    import datetime as dt
    UTC = dt.timezone.utc, datetime
from pathlib import Path
from typing import Any

from .descriptor import OperatorDescriptor

MAX_BUNDLE_BYTES = 262_144
MAX_BUNDLE_DESCRIPTORS = 128


@dataclass(frozen=True)
class BootstrapImportReport:
    """Bounded summary of one local Bundle parsing and signature-verification attempt."""

    accepted_count: int
    rejected_count: int


class BootstrapRegistry:
    """Manage a local collection of verified operator descriptors."""

    def __init__(self, descriptors: list[OperatorDescriptor] | None = None) -> None:
        self._descriptors: dict[str, OperatorDescriptor] = {}
        for descriptor in descriptors or []:
            self.add_descriptor(descriptor)

    def add_descriptor(self, descriptor: OperatorDescriptor) -> None:
        if not descriptor.verify_signature():
            raise ValueError("descriptor signature is invalid")
        self._descriptors[descriptor.operator_id] = descriptor

    def remove_expired(self, now: datetime | None = None) -> int:
        current = now or datetime.now(UTC)
        expired = [operator_id for operator_id, item in self._descriptors.items() if item.is_expired(current)]
        for operator_id in expired:
            del self._descriptors[operator_id]
        return len(expired)

    def get_active_operators(self, now: datetime | None = None) -> list[OperatorDescriptor]:
        current = now or datetime.now(UTC)
        return [item for item in self._descriptors.values() if not item.is_expired(current)]

    def export_bundle(self) -> str:
        payload = {
            "version": "1",
            "descriptors": [item.model_dump(mode="json") for item in self._descriptors.values()],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def import_bundle(self, data: str | bytes | dict[str, Any] | list[dict[str, Any]]) -> int:
        """Import a bundle and return the number of valid descriptors accepted."""
        return self.import_bundle_report(data).accepted_count

    def import_bundle_report(
        self, data: str | bytes | dict[str, Any] | list[dict[str, Any]]
    ) -> BootstrapImportReport:
        """Import a bounded bundle and return counts without retaining invalid descriptors."""
        payload = self._parse_bundle(data)
        raw_descriptors = self._extract_descriptors(payload)
        accepted = 0
        rejected = 0
        for raw in raw_descriptors:
            if not isinstance(raw, dict):
                rejected += 1
                continue
            try:
                descriptor = OperatorDescriptor.model_validate(raw)
                self.add_descriptor(descriptor)
            except (ValueError, TypeError):
                rejected += 1
                continue
            accepted += 1
        return BootstrapImportReport(accepted_count=accepted, rejected_count=rejected)

    @staticmethod
    def _parse_bundle(data: str | bytes | dict[str, Any] | list[dict[str, Any]]) -> Any:
        if isinstance(data, bytes):
            if len(data) > MAX_BUNDLE_BYTES:
                raise ValueError(f"bootstrap bundle exceeds {MAX_BUNDLE_BYTES} bytes")
            return json.loads(data)
        if isinstance(data, str):
            if len(data.encode("utf-8")) > MAX_BUNDLE_BYTES:
                raise ValueError(f"bootstrap bundle exceeds {MAX_BUNDLE_BYTES} bytes")
            return json.loads(data)
        return data

    @staticmethod
    def _extract_descriptors(payload: Any) -> list[Any]:
        if isinstance(payload, list):
            raw_descriptors = payload
        elif isinstance(payload, dict):
            raw_descriptors = payload.get("descriptors", [])
        else:
            raise ValueError("bootstrap bundle must be an object or list")
        if not isinstance(raw_descriptors, list):
            raise ValueError("bundle descriptors must be a list")
        if len(raw_descriptors) > MAX_BUNDLE_DESCRIPTORS:
            raise ValueError(f"bootstrap bundle exceeds {MAX_BUNDLE_DESCRIPTORS} descriptors")
        return raw_descriptors

    def save_to_file(self, path: str | Path) -> None:
        Path(path).write_text(self.export_bundle(), encoding="utf-8")

    def load_from_file(self, path: str | Path) -> int:
        target = Path(path)
        if target.stat().st_size > MAX_BUNDLE_BYTES:
            raise ValueError(f"bootstrap bundle exceeds {MAX_BUNDLE_BYTES} bytes")
        return self.import_bundle(target.read_bytes())

    def __len__(self) -> int:
        return len(self._descriptors)


__all__ = [
    "BootstrapImportReport",
    "BootstrapRegistry",
    "MAX_BUNDLE_BYTES",
    "MAX_BUNDLE_DESCRIPTORS",
]
