"""Point-in-time universe membership primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .models import InstrumentId, _require_aware


@dataclass(frozen=True, slots=True)
class UniverseInterval:
    instrument: InstrumentId
    valid_from: datetime
    valid_to: datetime | None = None

    def __post_init__(self) -> None:
        _require_aware(self.valid_from, "valid_from")
        if self.valid_to is not None:
            _require_aware(self.valid_to, "valid_to")
            if self.valid_to <= self.valid_from:
                raise ValueError("valid_to must be later than valid_from")

    def contains(self, instant: datetime) -> bool:
        _require_aware(instant, "instant")
        return self.valid_from <= instant and (self.valid_to is None or instant < self.valid_to)


def members_at(intervals: Iterable[UniverseInterval], instant: datetime) -> set[InstrumentId]:
    """Return the universe that was active at a historical instant."""

    _require_aware(instant, "instant")
    return {interval.instrument for interval in intervals if interval.contains(instant)}
