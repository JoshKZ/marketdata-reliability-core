from datetime import datetime, timedelta, timezone
from decimal import Decimal

from marketdata_reliability import Bar, InstrumentId, ValidationCode, validate_bars


UTC = timezone.utc
INSTRUMENT = InstrumentId("XNAS", "DEMO", "equity")


def make_bar(minute: int, **overrides: Decimal) -> Bar:
    values = {
        "open": Decimal("100"),
        "high": Decimal("101"),
        "low": Decimal("99"),
        "close": Decimal("100.5"),
        "volume": Decimal("10"),
    }
    values.update(overrides)
    start = datetime(2026, 1, 2, 14, minute, tzinfo=UTC)
    return Bar(
        instrument=INSTRUMENT,
        start=start,
        end=start + timedelta(minutes=1),
        **values,
    )


def test_detects_ohlc_and_volume_errors() -> None:
    issues = validate_bars(
        [make_bar(30, high=Decimal("99"), volume=Decimal("-1"))],
        expected_interval=timedelta(minutes=1),
    )
    assert {issue.code for issue in issues} == {
        ValidationCode.INVALID_OHLC,
        ValidationCode.NEGATIVE_VOLUME,
    }


def test_detects_duplicate_and_missing_intervals() -> None:
    first = make_bar(30)
    bars = [first, first, make_bar(32)]
    issues = validate_bars(bars, expected_interval=timedelta(minutes=1))
    codes = [issue.code for issue in issues]
    assert ValidationCode.DUPLICATE_BAR in codes
    assert ValidationCode.MISSING_INTERVAL in codes
