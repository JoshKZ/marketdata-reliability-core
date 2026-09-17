"""Small provenance primitives for derived market-data records."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from .models import _require_aware


@dataclass(frozen=True, slots=True)
class LineageRecord:
    """Describe how one derived record relates to immutable source observations."""

    lineage_id: str
    output_key: str
    transformation: str
    source_observation_ids: tuple[str, ...]
    created_at: datetime


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

    if not output_key.strip():
        raise ValueError("output_key must not be empty")
    if not transformation.strip():
        raise ValueError("transformation must not be empty")
    _require_aware(created_at, "created_at")

    sources = tuple(source_observation_ids)
    if not sources:
        raise ValueError("source_observation_ids must not be empty")
    if any(not source.strip() for source in sources):
        raise ValueError("source_observation_ids must not contain empty values")
    if len(set(sources)) != len(sources):
        raise ValueError("source_observation_ids must not contain duplicates")

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
