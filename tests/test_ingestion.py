from datetime import datetime, timezone

import pytest

from marketdata_reliability import (
    InMemoryObservationStore,
    InsertDisposition,
    InstrumentId,
    ObservationCollisionError,
    SourceObservation,
    build_observation,
)


def test_replaying_same_observation_is_idempotent() -> None:
    instrument = InstrumentId("XNAS", "DEMO", "equity")
    observed_at = datetime(2026, 1, 2, 14, 31, tzinfo=timezone.utc)
    observation = build_observation(
        provider="synthetic",
        instrument=instrument,
        event_time=datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc),
        observed_at=observed_at,
        request_id="request-1",
        payload={"close": "100.5", "volume": 1200},
    )

    store = InMemoryObservationStore()
    assert store.insert(observation) is InsertDisposition.INSERTED
    assert store.insert(observation) is InsertDisposition.DUPLICATE
    assert len(store) == 1


def test_same_id_with_different_evidence_is_a_collision() -> None:
    instrument = InstrumentId("XNAS", "DEMO", "equity")
    first = SourceObservation(
        observation_id="same-id",
        provider="synthetic",
        instrument=instrument,
        event_time=datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc),
        observed_at=datetime(2026, 1, 2, 14, 31, tzinfo=timezone.utc),
        request_id="request-1",
        payload=b"one",
    )
    second = SourceObservation(
        observation_id="same-id",
        provider="synthetic",
        instrument=instrument,
        event_time=first.event_time,
        observed_at=first.observed_at,
        request_id="request-1",
        payload=b"two",
    )

    store = InMemoryObservationStore()
    store.insert(first)
    with pytest.raises(ObservationCollisionError):
        store.insert(second)
