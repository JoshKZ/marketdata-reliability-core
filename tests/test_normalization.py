from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from marketdata_reliability import (
    BarFieldMap,
    InstrumentId,
    NormalizationError,
    normalize_bar,
)

UTC = timezone.utc
INSTRUMENT = InstrumentId("XNAS", "DEMO", "equity")
START = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
END = START + timedelta(minutes=1)


def test_normalizes_custom_provider_fields_without_vendor_dependency() -> None:
    record: dict[str, object] = {
        "px_open": "100.10",
        "px_high": Decimal("101.20"),
        "px_low": 99,
        "px_close": "100.75",
        "qty": "1200",
    }
    fields = BarFieldMap(
        open="px_open",
        high="px_high",
        low="px_low",
        close="px_close",
        volume="qty",
    )

    bar = normalize_bar(
        record,
        instrument=INSTRUMENT,
        start=START,
        end=END,
        fields=fields,
        source_observation_id="obs-1",
    )

    assert bar.open == Decimal("100.10")
    assert bar.high == Decimal("101.20")
    assert bar.low == Decimal(99)
    assert bar.close == Decimal("100.75")
    assert bar.volume == Decimal(1200)
    assert bar.source_observation_id == "obs-1"


def test_missing_provider_field_fails_loudly() -> None:
    record: dict[str, object] = {
        "open": "100",
        "high": "101",
        "low": "99",
        "close": "100.5",
    }

    with pytest.raises(NormalizationError, match="missing required provider field: volume"):
        normalize_bar(record, instrument=INSTRUMENT, start=START, end=END)


def test_float_input_is_rejected_instead_of_silently_round_tripping() -> None:
    record: dict[str, object] = {
        "open": 100.1,
        "high": "101",
        "low": "99",
        "close": "100.5",
        "volume": 10,
    }

    with pytest.raises(NormalizationError, match="is a float"):
        normalize_bar(record, instrument=INSTRUMENT, start=START, end=END)


def test_non_finite_decimal_is_rejected() -> None:
    record: dict[str, object] = {
        "open": "NaN",
        "high": "101",
        "low": "99",
        "close": "100.5",
        "volume": 10,
    }

    with pytest.raises(NormalizationError, match="must be finite"):
        normalize_bar(record, instrument=INSTRUMENT, start=START, end=END)
