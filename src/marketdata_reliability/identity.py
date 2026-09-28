"""Opt-in v2 identities and read-only observation migration planning."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from ._identity import (
    OBSERVATION_PREFIX,
    fingerprint,
    instrument_parts,
    lineage_fingerprint,
    observation_fingerprint,
    text_bytes,
)
from .models import InstrumentId, SourceObservation, _utc_iso, build_observation
from .provenance import LineageRecord, _validate_lineage_parts


class IdentityMigrationError(ValueError):
    """A migration cannot safely identify its input; no partial plan is returned."""


@dataclass(frozen=True, slots=True)
class IdentityMigration:
    """One input row's old/new ID mapping, not proof of a database write."""

    source_index: int
    old_id: str
    new_id: str


def instrument_key_v2(instrument: InstrumentId) -> str:
    """Return a namespaced key without delimiter ambiguity or Unicode normalization."""
    if not isinstance(instrument, InstrumentId):
        raise TypeError("instrument must be InstrumentId")
    return fingerprint("instrument", instrument_parts(
        instrument.market, instrument.symbol, instrument.asset_class,
    ))


def _observation_id(record: SourceObservation) -> str:
    if not isinstance(record.instrument, InstrumentId):
        raise TypeError("instrument must be InstrumentId")
    return observation_fingerprint(
        record.provider, record.instrument.market, record.instrument.symbol,
        record.instrument.asset_class, _utc_iso(record.event_time), record.request_id,
        record.payload,
    )


def build_observation_v2(
    *, provider: str, instrument: InstrumentId, event_time: datetime,
    observed_at: datetime, request_id: str, payload: Mapping[str, Any],
) -> SourceObservation:
    """Build opt-in versioned evidence; preserve legacy payload-byte serialization.

    IDs hash stored payload bytes, not the original Python types. observed_at is
    still metadata excluded from identity and must be preserved during replays.
    Legacy build_observation and existing IDs are not changed by this function.
    """
    text_bytes(provider, "provider")
    text_bytes(request_id, "request_id")
    if not isinstance(instrument, InstrumentId):
        raise TypeError("instrument must be InstrumentId")
    if not isinstance(event_time, datetime) or not isinstance(observed_at, datetime):
        raise TypeError("event_time and observed_at must be datetime")
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    record = build_observation(
        provider=provider, instrument=instrument, event_time=event_time,
        observed_at=observed_at, request_id=request_id, payload=payload,
    )
    return replace(record, observation_id=_observation_id(record))


def build_lineage_v2(
    *, output_key: str, transformation: str, source_observation_ids: Iterable[str],
    created_at: datetime,
) -> LineageRecord:
    """Build namespaced lineage; source order matters and creation time does not.

    References are caller-supplied opaque IDs. This neither verifies their
    existence nor rewrites legacy references to v2 observation IDs.
    """
    if isinstance(source_observation_ids, (str, bytes)):
        raise TypeError("source_observation_ids must be an iterable of IDs, not one string")
    sources = tuple(source_observation_ids)
    new_id = lineage_fingerprint(output_key, transformation, sources)
    _validate_lineage_parts(output_key, transformation, sources, created_at)
    return LineageRecord(new_id, output_key, transformation, sources, created_at)


def _legacy_observation_id(record: SourceObservation) -> str:
    """Reproduce v1 from exact stored bytes, never decode/re-serialize a payload."""
    digest = hashlib.sha256()
    for part in (record.provider, record.instrument.stable_key(),
                 _utc_iso(record.event_time), record.request_id):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x1f")
    digest.update(record.payload)
    return digest.hexdigest()


def plan_observation_migration(
    observations: Iterable[SourceObservation], *, max_records: int = 100_000,
) -> tuple[IdentityMigration, ...]:
    """Plan v1-to-v2 ID mappings without changing records, payloads, or storage.

    Verify each old fingerprint against its evidence. A legacy ID mapping to
    multiple v2 IDs aborts instead of losing a row in a dictionary. Input rows,
    including duplicates, retain their indices. Verified v2 IDs map to themselves.
    Custom IDs cannot be inferred. Limits are checked; nothing is truncated.
    Callers own full-scope reconciliation, foreign keys, transactions, and backups.
    """
    if type(max_records) is not int or max_records <= 0:
        raise ValueError("max_records must be a positive integer")
    mappings: dict[str, str] = {}
    result: list[IdentityMigration] = []
    for index, record in enumerate(observations):
        if index >= max_records:
            raise IdentityMigrationError("migration exceeds max_records; no complete plan")
        if not isinstance(record, SourceObservation):
            raise TypeError("observations must contain SourceObservation objects")
        new_id = _observation_id(record)
        expected = (new_id if record.observation_id.startswith(OBSERVATION_PREFIX)
                    else _legacy_observation_id(record))
        if record.observation_id != expected:
            raise IdentityMigrationError(f"unverifiable observation identity at index {index}")
        previous = mappings.get(record.observation_id)
        if previous is not None and previous != new_id:
            raise IdentityMigrationError(f"ambiguous legacy observation identity at index {index}")
        mappings[record.observation_id] = new_id
        result.append(IdentityMigration(index, record.observation_id, new_id))
    return tuple(result)
