from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from marketdata_reliability import (
    Bar,
    InstrumentId,
    ValidationCode,
    ValidationSeverity,
    ValidationWindow,
    audit_bars,
    report_to_dict,
    report_to_json,
)

T = datetime(2026, 1, 2, 9, tzinfo=UTC)
I = InstrumentId("SYNTH", "DEMO", "equity")


def bar(instrument=I, start=T, end=None, close=Decimal("100")):
    return Bar(instrument, start, end or start + timedelta(minutes=1),
               Decimal("100"), Decimal("101"), Decimal("99"), close, Decimal("10"))


def test_json_projection_is_detached_and_deterministic():
    import json

    report = audit_bars([bar()], windows=[ValidationWindow(I, T, T + timedelta(minutes=3),
                                                         timedelta(minutes=1))])
    document = report_to_dict(report)
    assert document["schema_version"] == "1.0"
    assert document["coverage_basis"] == "presence_not_validity"
    assert document["summary"]["coverage_ratio"] == "0.3333333333333333333333333333"
    assert document["summary"]["missing_bars"] == 2
    assert document["windows"][0]["interval_microseconds"] == 60_000_000
    assert document["windows"][0]["missing_timestamps"] == [
        "2026-01-02T09:01:00.000000+00:00", "2026-01-02T09:02:00.000000+00:00",
    ]
    assert document["issues"][0]["index"] is None
    assert document["issues"][0]["window_index"] == 0
    before = report_to_json(report)
    assert json.loads(before) == document
    document["summary"]["covered_bars"] = 999
    document["windows"][0]["missing_timestamps"].clear()
    assert report_to_json(report) == before
    assert report.covered_bars == 1 and report.missing_bars == 2


def test_coverage_one_does_not_hide_invalid_prices():
    import json

    report = audit_bars([bar(close=Decimal("NaN"))], windows=[
        ValidationWindow(I, T, T + timedelta(minutes=1), timedelta(minutes=1)),
    ])
    text = report_to_json(report)
    data = json.loads(text)
    assert data["summary"]["coverage_ratio"] == "1"
    assert data["summary"]["valid"] is False
    assert data["issues"][0]["code"] == "non_finite_value"
    assert "NaN" not in text and "close\":" not in text


def test_unexpected_instrument_has_null_coverage_and_structured_identity():
    unexpected = InstrumentId("OTHER", "DEMO", "equity")
    report = audit_bars([bar(unexpected)], windows=[
        ValidationWindow(I, T, T + timedelta(minutes=1), timedelta(minutes=1)),
    ])
    data = report_to_dict(report)
    item = next(x for x in data["instruments"] if x["instrument"]["market"] == "OTHER")
    assert item["summary"]["coverage_ratio"] is None
    assert item["outside_window_bars"] == 1
    assert data["outside_window_bars"] == 1


def test_delimiter_collisions_do_not_collapse_instrument_objects():
    first = InstrumentId("A", "D", "B:C")
    second = InstrumentId("A:B", "D", "C")
    assert first.stable_key() == second.stable_key()
    report = audit_bars([bar(first), bar(second)], windows=[
        ValidationWindow(i, T, T + timedelta(minutes=1), timedelta(minutes=1))
        for i in (first, second)
    ])
    data = report_to_dict(report)
    assert len(data["instruments"]) == 2
    assert data["instruments"][0]["instrument"] != data["instruments"][1]["instrument"]
    assert data["summary"]["covered_bars"] == 2


def test_warn_policy_is_preserved_in_json():
    report = audit_bars([], windows=[
        ValidationWindow(I, T, T + timedelta(minutes=1), timedelta(minutes=1)),
    ], severity_overrides={ValidationCode.MISSING_INTERVAL: ValidationSeverity.WARNING})
    data = report_to_dict(report)
    assert data["summary"]["valid"] is True
    assert data["summary"]["missing_bars"] == 1
    assert data["summary"]["warning_count"] == 1
    assert data["issues"][0]["severity"] == "warning"


def test_exact_microsecond_intervals_and_unicode_are_json_safe():
    import json

    instrument = InstrumentId("SYNTH", "\u6e2c\u8a66\"\\\n", "equity")
    window = ValidationWindow(instrument, T, T + timedelta(microseconds=2), timedelta(microseconds=1))
    report = audit_bars([], windows=[window])
    text = report_to_json(report, indent=None)
    assert text.isascii()
    assert "\u6e2c\u8a66" not in text
    assert json.loads(text)["windows"][0]["interval_microseconds"] == 1
    assert json.loads(text)["windows"][0]["instrument"]["symbol"] == instrument.symbol


@pytest.mark.parametrize("indent", [-1, 9, True, 1.5, "2"])
def test_indent_rejects_invalid_configuration(indent):
    report = audit_bars([], windows=[ValidationWindow(I, T, T + timedelta(minutes=1),
                                                    timedelta(minutes=1))])
    with pytest.raises(ValueError):
        report_to_json(report, indent=indent)


def test_projection_requires_a_completed_report():
    with pytest.raises(TypeError):
        report_to_dict({"valid": True})
