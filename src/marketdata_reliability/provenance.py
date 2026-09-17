"""Small provenance primitives for derived market-data records."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from .models import _require_aware


def _validate_lineage_parts(
    output_key: str,
    transformation: str,
    source_observation_ids: tuple[str, ...],
    created_at: datetime,
) -> None:
    if not output_key.strip():
        raise ValueError("output_key must not be empty")
    if not transformation.strip():
        raise ValueError("transformation must not be empty")
    if not source_observation_ids:
        raise ValueError("source_observation_ids must not be empty")
    if any(not source.strip() for source in source_observation_ids):
        raise ValueError("source_observation_ids must not contain empty values")
    if len(set(source_observation_ids)) != len(source_observation_ids):
        raise ValueError("source_observation_ids must not contain duplicates")
    _require_aware(created_at, "created_at")


@dataclass(frozen=True, slots=True)
class LineageRecord:
    """Describe how one derived record relates to immutable source observations."""

    lineage_id: str
    output_key: str
    transformation: str
    source_observation_ids: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if len(self.lineage_id) != 64 or self.lineage_id != self.lineage_id.lower():
            raise ValueError("lineage_id must be a lowercase SHA-256 hex digest")
        try:
            int(self.lineage_id, 16)
        except ValueError as exc:
            raise ValueError("lineage_id must be a lowercase SHA-256 hex digest") from exc
        _validate_lineage_parts(
            self.output_key,
            self.transformation,
            self.source_observation_ids,
            self.created_at,
        )


def build_lineage(
    *,
    output_key: str,
    transformation: str,
    source_observation_ids: Iterable[str],
    created_at: datetime,
) -> LineageRecord:
    """Build deterministic lineage identity for a derived record.

    Source order is significant. Callers should supply a stable semantic order, such as
    chronological bar order. ``created_at`` is audit metadata and does not affect the
    deterministic lineage ID.
    """

    sources = tuple(source_observation_ids)
    _validate_lineage_parts(output_key, transformation, sources, created_at)

    digest = hashlib.sha256()
    for part in (output_key, transformation, *sources):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x1f")

    return LineageRecord(
        lineage_id=digest.hexdigest(),
        output_key=output_key,
        transformation=transformation,
        source_observation_ids=sources,
        created_at=created_at,
    )
