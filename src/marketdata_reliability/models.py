"""Immutable canonical models and source-observation helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _utc_iso(value: datetime) -> str:
    _require_aware(value, "datetime")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return _utc_iso(value)
    raise TypeError(f"unsupported payload type: {type(value).__name__}")


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Encode a mapping deterministically for fingerprinting and storage."""

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True, order=True)
class InstrumentId:
    """Provider-independent instrument identity."""

    market: str
    symbol: str
    asset_class: str = "unknown"

    def __post_init__(self) -> None:
        if not self.market.strip():
            raise ValueError("market must not be empty")
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if not self.asset_class.strip():
            raise ValueError("asset_class must not be empty")

    def stable_key(self) -> str:
        return f"{self.market}:{self.asset_class}:{self.symbol}"


@dataclass(frozen=True, slots=True)
class SourceObservation:
    """Immutable evidence captured from a source request or feed event."""

    observation_id: str
    provider: str
    instrument: InstrumentId
    event_time: datetime
    observed_at: datetime
    request_id: str
    payload: bytes

    def __post_init__(self) -> None:
        if not self.observation_id.strip():
            raise ValueError("observation_id must not be empty")
        if not self.provider.strip():
            raise ValueError("provider must not be empty")
        if not self.request_id.strip():
            raise ValueError("request_id must not be empty")
        _require_aware(self.event_time, "event_time")
        _require_aware(self.observed_at, "observed_at")


def build_observation(
    *,
    provider: str,
    instrument: InstrumentId,
    event_time: datetime,
    observed_at: datetime,
    request_id: str,
    payload: Mapping[str, Any],
) -> SourceObservation:
    """Build an immutable observation with a deterministic content fingerprint.

    `request_id` should be stable when the same source evidence is replayed. The
    observation timestamp is deliberately metadata rather than part of the fingerprint;
    a replay should preserve the original `observed_at` value.
    """

    if not provider.strip():
        raise ValueError("provider must not be empty")
    if not request_id.strip():
        raise ValueError("request_id must not be empty")
    _require_aware(event_time, "event_time")
    _require_aware(observed_at, "observed_at")

    payload_bytes = canonical_json_bytes(payload)
    digest = hashlib.sha256()
    for part in (
        provider,
        instrument.stable_key(),
        _utc_iso(event_time),
        request_id,
    ):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x1f")
    digest.update(payload_bytes)

    return SourceObservation(
        observation_id=digest.hexdigest(),
        provider=provider,
        instrument=instrument,
        event_time=event_time,
        observed_at=observed_at,
        request_id=request_id,
        payload=payload_bytes,
    )


@dataclass(frozen=True, slots=True)
class Bar:
    """Canonical OHLCV bar."""

    instrument: InstrumentId
    start: datetime
    end: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    source_observation_id: str | None = None

    def __post_init__(self) -> None:
        _require_aware(self.start, "start")
        _require_aware(self.end, "end")
