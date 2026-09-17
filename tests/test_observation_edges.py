from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from marketdata_reliability import InstrumentId, build_observation

UTC = timezone.utc
TPE = timezone(timedelta(hours=8))
INSTRUMENT = InstrumentId("XNAS", "DEMO", "equity")


def test_fingerprint_is_stable_across_mapping_order_and_equivalent_timezones() -> None:
    first = build_observation(
        provider="synthetic",
        instrument=INSTRUMENT,
        event_time=datetime(2026, 1, 2, 14, 30, tzinfo=UTC),
        observed_at=datetime(2026, 1, 2, 14, 31, tzinfo=UTC),
        request_id="request-1",
        payload={"close": Decimal("100.50"), "volume": 1200},
    )
    second = build_observation(
        provider="synthetic",
        instrument=INSTRUMENT,
        event_time=datetime(2026, 1, 2, 22, 30, tzinfo=TPE),
        observed_at=datetime(2026, 1, 2, 14, 40, tzinfo=UTC),
        request_id="request-1",
        payload={"volume": 1200, "close": Decimal("100.50")},
    )

    assert first.observation_id == second.observation_id
    assert first.payload == second.payload


def test_naive_event_or_observation_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="event_time must be timezone-aware"):
        build_observation(
            provider="synthetic",
            instrument=INSTRUMENT,
            event_time=datetime(2026, 1, 2, 14, 30),
            observed_at=datetime(2026, 1, 2, 14, 31, tzinfo=UTC),
            request_id="request-1",
            payload={"close": "100.5"},
        )

    with pytest.raises(ValueError, match="observed_at must be timezone-aware"):
        build_observation(
            provider="synthetic",
            instrument=INSTRUMENT,
            event_time=datetime(2026, 1, 2, 14, 30, tzinfo=UTC),
            observed_at=datetime(2026, 1, 2, 14, 31),
            request_id="request-1",
            payload={"close": "100.5"},
        )
