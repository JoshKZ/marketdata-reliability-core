"""Offline audit: two synthetic sessions, two holes, one duplicate, one bad high."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from marketdata_reliability import (
    InstrumentId,
    ValidationCode,
    ValidationReport,
    ValidationWindow,
    audit_bars,
    normalize_bar,
)


def run_demo() -> ValidationReport:
    instrument = InstrumentId("SYNTH", "DEMO", "equity")
    morning = datetime(2026, 1, 2, 9, tzinfo=UTC)
    afternoon = morning + timedelta(hours=4)
    minute = timedelta(minutes=1)
    windows = [ValidationWindow(instrument, t, t + 5 * minute, minute)
               for t in (morning, afternoon)]
    bars = []
    for start, present in ((morning, (0, 1, 3, 4)), (afternoon, (0, 1, 2, 4))):
        for offset in present:
            instant = start + offset * minute
            record = {"open": "100", "high": "101", "low": "99",
                      "close": "100.5", "volume": 10}
            if start == afternoon and offset == 2:
                record["high"] = "99.5"
            bars.append(normalize_bar(record, instrument=instrument,
                                      start=instant, end=instant + minute))
    bars.append(bars[0])
    report = audit_bars(bars, windows=windows)
    # These assertions are also exercised against the installed wheel in CI.
    assert (report.expected_bars, report.observed_bars, report.covered_bars) == (10, 9, 8)
    assert report.missing_timestamps[instrument] == (morning + 2 * minute, afternoon + 3 * minute)
    assert report.coverage_ratio == Decimal("0.8")
    assert report.count_by_code == {
        ValidationCode.INVALID_OHLC: 1,
        ValidationCode.DUPLICATE_BAR: 1,
        ValidationCode.MISSING_INTERVAL: 2,
    }
    assert not report.valid
    print(f"expected={report.expected_bars}, observed={report.observed_bars}, "
          f"covered={report.covered_bars}, missing={report.missing_bars}, "
          f"duplicates={report.duplicate_bars}")
    print(f"coverage={report.coverage_ratio}, valid={report.valid}, errors={report.error_count}")
    for issue in report.issues:
        print(f"{issue.severity.value}: {issue.code.value}: {issue.message}")
    return report


if __name__ == "__main__":
    run_demo()
