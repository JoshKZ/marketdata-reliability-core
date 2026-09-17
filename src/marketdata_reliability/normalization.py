"""Explicit, provider-independent normalization into canonical market-data models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import Bar, InstrumentId


class NormalizationError(ValueError):
    """Raised when provider-shaped input cannot be normalized safely."""


@dataclass(frozen=True, slots=True)
class BarFieldMap:
    """Map provider field names to the canonical OHLCV bar contract."""

    open: str = "open"
    high: str = "high"
    low: str = "low"
    close: str = "close"
    volume: str = "volume"

    def __post_init__(self) -> None:
        values = (self.open, self.high, self.low, self.close, self.volume)
        if any(not value.strip() for value in values):
            raise ValueError("bar field names must not be empty")
        if len(set(values)) != len(values):
            raise ValueError("bar field names must be unique")


def _required(record: Mapping[str, object], field_name: str) -> object:
    try:
        return record[field_name]
    except KeyError as exc:
        raise NormalizationError(f"missing required provider field: {field_name}") from exc


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise NormalizationError(f"{field_name} must be a decimal-compatible value, not bool")
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, str):
        try:
            result = Decimal(value)
        except InvalidOperation as exc:
            raise NormalizationError(f"{field_name} is not a valid decimal value") from exc
    elif isinstance(value, float):
        raise NormalizationError(
            f"{field_name} is a float; convert it to Decimal or a decimal string upstream"
        )
    else:
        raise NormalizationError(
            f"{field_name} must be Decimal, int, or a decimal string"
        )

    if not result.is_finite():
        raise NormalizationError(f"{field_name} must be finite")
    return result


def normalize_bar(
    record: Mapping[str, object],
    *,
    instrument: InstrumentId,
    start: datetime,
    end: datetime,
    fields: BarFieldMap | None = None,
    source_observation_id: str | None = None,
) -> Bar:
    """Normalize a provider-shaped mapping into a canonical :class:`Bar`.

    Timestamp parsing is intentionally outside this function: provider timestamps are
    often ambiguous, so callers must resolve them into timezone-aware datetimes before
    normalization. Float prices are rejected to avoid silently importing binary-float
    artifacts into canonical financial values.
    """

    selected = fields or BarFieldMap()
    if source_observation_id is not None and not source_observation_id.strip():
        raise NormalizationError("source_observation_id must not be empty")

    return Bar(
        instrument=instrument,
        start=start,
        end=end,
        open=_decimal(_required(record, selected.open), selected.open),
        high=_decimal(_required(record, selected.high), selected.high),
        low=_decimal(_required(record, selected.low), selected.low),
        close=_decimal(_required(record, selected.close), selected.close),
        volume=_decimal(_required(record, selected.volume), selected.volume),
        source_observation_id=source_observation_id,
    )
