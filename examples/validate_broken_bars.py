"""Small demo: detect common quality failures without any external provider."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from marketdata_reliability import Bar, InstrumentId, validate_bars


utc = timezone.utc
instrument = InstrumentId("DEMO", "ABC", "equity")


def bar(minute: int, *, high: str = "101", volume: str = "100") -> Bar:
    start = datetime(2026, 1, 2, 9, minute, tzinfo=utc)
    return Bar(
        instrument=instrument,
        start=start,
        end=start + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal(high),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal(volume),
    )


bars = [
    bar(30),
    bar(30),  # duplicate
    bar(32, high="99.5", volume="-1"),  # minute 31 missing; invalid OHLC and volume
]

for issue in validate_bars(bars, expected_interval=timedelta(minutes=1)):
    print(f"{issue.code.value}: {issue.message}")
