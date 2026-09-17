from datetime import datetime, timezone

from marketdata_reliability import InstrumentId, UniverseInterval, members_at


def test_membership_uses_historical_interval_not_present_day_list() -> None:
    utc = timezone.utc
    old = InstrumentId("TEST", "OLD", "equity")
    new = InstrumentId("TEST", "NEW", "equity")
    intervals = [
        UniverseInterval(
            old,
            valid_from=datetime(2020, 1, 1, tzinfo=utc),
            valid_to=datetime(2022, 1, 1, tzinfo=utc),
        ),
        UniverseInterval(new, valid_from=datetime(2024, 1, 1, tzinfo=utc)),
    ]

    assert members_at(intervals, datetime(2021, 6, 1, tzinfo=utc)) == {old}
    assert members_at(intervals, datetime(2025, 6, 1, tzinfo=utc)) == {new}
