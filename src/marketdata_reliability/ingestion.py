"""Idempotent ingestion primitives."""

from __future__ import annotations

from enum import Enum
from typing import Iterable

from .models import SourceObservation


class InsertDisposition(str, Enum):
    INSERTED = "inserted"
    DUPLICATE = "duplicate"


class ObservationCollisionError(ValueError):
    """Raised when an observation ID is reused for different immutable evidence."""


class InMemoryObservationStore:
    """Reference store demonstrating idempotent observation semantics.

    Production persistence adapters can implement the same semantics without making
    this project depend on a particular database.
    """

    def __init__(self) -> None:
        self._items: dict[str, SourceObservation] = {}

    def insert(self, observation: SourceObservation) -> InsertDisposition:
        existing = self._items.get(observation.observation_id)
        if existing is None:
            self._items[observation.observation_id] = observation
            return InsertDisposition.INSERTED
        if existing == observation:
            return InsertDisposition.DUPLICATE
        raise ObservationCollisionError(
            "observation_id already exists with different immutable evidence"
        )

    def insert_many(self, observations: Iterable[SourceObservation]) -> list[InsertDisposition]:
        return [self.insert(observation) for observation in observations]

    def get(self, observation_id: str) -> SourceObservation | None:
        return self._items.get(observation_id)

    def __len__(self) -> int:
        return len(self._items)
