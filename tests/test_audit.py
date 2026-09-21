"""Executable session-audit contracts; all instruments and prices are synthetic."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, Inexact, localcontext
from itertools import combinations
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from marketdata_reliability import (
    Bar,
    InstrumentId,
    ValidationCode,
    ValidationIssue,
    ValidationSeverity,
    ValidationWindow,
    audit_bars,
    validate_bar,
    validate_bars,
)

A = InstrumentId("SYNTH", "AAA", "equity")
B = InstrumentId("SYNTH", "BBB", "equity")
T = datetime(2026, 1, 2, 9, tzinfo=UTC)
STEP = timedelta(minutes=1)


def window(start: datetime = T, count: int = 5, instrument: InstrumentId = A) -> ValidationWindow:
    return ValidationWindow(instrument, start, start + count * STEP, STEP)


def bar(start: datetime = T, instrument: InstrumentId = A, **changes: Any) -> Bar:
    return replace(
        Bar(instrument, start, start + STEP, Decimal(100), Decimal(101),
            Decimal(99), Decimal(100), Decimal(10)),
        **changes,
    )


def test_two_sessions_ignore_break_but_find_exact_missing_slots() -> None:
    afternoon = T + timedelta(hours=4)
    rows = [bar(T + i * STEP) for i in (0, 1, 3, 4)]
    rows += [bar(afternoon + i * STEP) for i in (0, 1, 2, 4)]
    rows += [rows[0]]
    report = audit_bars(rows, windows=[window(), window(afternoon)])
    assert (report.expected_bars, report.observed_bars, report.covered_bars) == (10, 9, 8)
    assert report.missing_bars == 2
    assert report.duplicate_bars == 1
    assert report.coverage_ratio == Decimal("0.8")
    assert report.missing_timestamps[A] == (T + 2 * STEP, afternoon + 3 * STEP)
    assert report.count_by_code == {
        ValidationCode.DUPLICATE_BAR: 1, ValidationCode.MISSING_INTERVAL: 2,
    }
    assert not report.valid
    assert report.error_count == 3
    assert [w.missing_bars for w in report.windows] == [1, 1]


def test_leading_trailing_and_entirely_empty_windows() -> None:
    report = audit_bars([bar(T + 2 * STEP)], windows=[window(), window(instrument=B)])
    assert report.missing_bars == 9
    assert report.windows[0].missing_timestamps == tuple(T + i * STEP for i in (0, 1, 3, 4))
    assert report.windows[1].coverage_ratio == Decimal(0)
    missing = [x for x in report.issues if x.code is ValidationCode.MISSING_INTERVAL]
    assert len(missing) == 9
    assert all(x.index is None and x.timestamp is not None for x in missing)
    assert {x.instrument for x in missing} == {A, B}


def test_half_open_boundaries_and_adjacent_windows() -> None:
    report = audit_bars([bar(T), bar(T + STEP), bar(T + 2 * STEP)],
                        windows=[window(count=1), window(T + STEP, count=1)])
    assert report.covered_bars == 2
    assert report.outside_window_bars == 1
    assert [w.observed_bars for w in report.windows] == [1, 1]
    outside = [x for x in report.issues if x.code is ValidationCode.OUTSIDE_WINDOW]
    assert outside[0].index == 2
    assert outside[0].window_index is None


def test_outside_and_unexpected_instruments_are_not_silently_dropped() -> None:
    rows = [bar(T - STEP), bar(T, B), bar(T)]
    report = audit_bars(rows, windows=[window(count=1)])
    assert report.observed_bars == 3
    assert report.outside_window_bars == 2
    assert report.coverage_ratio == Decimal(1)
    assert not report.valid
    assert report.by_instrument[B].expected_bars == 0
    assert report.by_instrument[B].coverage_ratio is None
    assert report.by_instrument[B].observed_bars == 1
    assert report.by_instrument[A].observed_bars == 2


@pytest.mark.parametrize("changes", [
    {"start": T + timedelta(seconds=30), "end": T + timedelta(seconds=90)},
    {"end": T + 2 * STEP},
    {"end": T},
    {"end": T - STEP},
])
def test_wrong_slots_do_not_inflate_coverage(changes: dict[str, datetime]) -> None:
    report = audit_bars([bar(**changes)], windows=[window(count=1)])
    assert report.covered_bars == 0
    assert report.missing_bars == 1
    assert ValidationCode.MISALIGNED_BAR in report.count_by_code
    assert not report.valid


def test_ohlc_invalid_bar_counts_as_present_not_valid() -> None:
    report = audit_bars([bar(high=Decimal(98))], windows=[window(count=1)])
    assert report.coverage_ratio == Decimal(1)
    assert not report.valid
    assert report.count_by_code[ValidationCode.INVALID_OHLC] == 1


@pytest.mark.parametrize("field", ["open", "high", "low", "close", "volume"])
@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"),
                                  Decimal("-Infinity")])
def test_nonfinite_direct_bars_report_instead_of_crashing(field: str, value: Decimal) -> None:
    row = bar(**{field: value})
    assert ValidationCode.NON_FINITE_VALUE in {x.code for x in validate_bar(row)}
    report = audit_bars([row], windows=[window(count=1)])
    assert not report.valid
    assert report.coverage_ratio == Decimal(1)


@pytest.mark.parametrize("value", [None, True, 1.25, "100", 100])
def test_invalid_direct_numeric_types_are_reported(value: object) -> None:
    report = audit_bars([bar(open=value)], windows=[window(count=1)])
    assert report.count_by_code[ValidationCode.INVALID_NUMERIC_TYPE] == 1
    assert not report.valid


def test_duplicate_count_is_extra_rows_not_slots() -> None:
    report = audit_bars([bar(), bar(), bar()], windows=[window(count=1)])
    assert report.observed_bars == 3
    assert report.duplicate_bars == 2
    assert report.covered_bars == 1
    assert report.count_by_code[ValidationCode.DUPLICATE_BAR] == 2


def test_conflicting_duplicate_never_selects_a_winner() -> None:
    report = audit_bars([bar(), bar(close=Decimal("100.5"))], windows=[window(count=1)])
    assert report.count_by_code[ValidationCode.DUPLICATE_BAR] == 1
    assert report.count_by_code[ValidationCode.CONFLICTING_DUPLICATE] == 1
    assert report.covered_bars == 1
    assert not report.valid


def test_numerically_equal_decimals_are_not_conflicting_duplicates() -> None:
    report = audit_bars([bar(), bar(close=Decimal("100.00"))], windows=[window(count=1)])
    assert ValidationCode.CONFLICTING_DUPLICATE not in report.count_by_code


def test_invalid_duplicate_values_do_not_crash_comparison() -> None:
    for value in (Decimal("sNaN"), None):
        report = audit_bars([bar(open=value), bar(open=value)], windows=[window(count=1)])
        assert not report.valid
        assert report.duplicate_bars == 1


def test_policy_is_explicit_does_not_change_counts_or_legacy_behavior() -> None:
    policy = {ValidationCode.MISSING_INTERVAL: ValidationSeverity.WARNING}
    report = audit_bars([], windows=[window(count=1)], severity_overrides=policy)
    policy.clear()
    assert report.valid
    assert report.warning_count == 1 and report.error_count == 0
    assert report.missing_bars == 1 and report.coverage_ratio == Decimal(0)
    assert ValidationIssue(ValidationCode.INVALID_OHLC, "old", 3).severity is ValidationSeverity.ERROR
    assert all(x.severity is ValidationSeverity.ERROR for x in validate_bars([bar(), bar()]))


@pytest.mark.parametrize("policy", [{"missing_interval": ValidationSeverity.WARNING},
                                    {ValidationCode.MISSING_INTERVAL: "warning"}])
def test_invalid_policies_rejected_before_consuming_input(policy: Any) -> None:
    def rows() -> Any:
        pytest.fail("invalid configuration must be checked before reading bars")
        yield bar()
    with pytest.raises(TypeError):
        audit_bars(rows(), windows=[window()], severity_overrides=policy)


def test_windows_and_reports_are_immutable_snapshots() -> None:
    windows = [window(count=1)]
    rows = [bar()]
    report = audit_bars(rows, windows=windows)
    windows.clear()
    rows.clear()
    assert report.expected_bars == 1 and report.observed_bars == 1
    with pytest.raises(FrozenInstanceError):
        report.covered_bars = 8  # type: ignore[misc]
    with pytest.raises(TypeError):
        report.count_by_code[ValidationCode.INVALID_OHLC] = 10  # type: ignore[index]
    with pytest.raises(TypeError):
        report.by_instrument[A] = report.by_instrument[A]  # type: ignore[index]
    with pytest.raises(TypeError):
        report.missing_timestamps[A] = ()  # type: ignore[index]
    assert isinstance(report.issues, tuple) and isinstance(report.windows, tuple)


@pytest.mark.parametrize("start,end,step", [
    (T.replace(tzinfo=None), T + STEP, STEP),
    (T, (T + STEP).replace(tzinfo=None), STEP),
    (T, T, STEP), (T + STEP, T, STEP),
    (T, T + STEP, timedelta(0)), (T, T + STEP, -STEP),
    (T, T + timedelta(seconds=90), STEP),
])
def test_invalid_window_contracts(start: datetime, end: datetime, step: timedelta) -> None:
    with pytest.raises(ValueError):
        ValidationWindow(A, start, end, step)


@pytest.mark.parametrize("windows", [[], [window(), window()],
                                     [window(), window(T + STEP)],
                                     [window(T + STEP), window()]])
def test_empty_or_overlapping_scope_rejected(windows: list[ValidationWindow]) -> None:
    with pytest.raises(ValueError):
        audit_bars([], windows=windows)


def test_different_instruments_can_overlap_and_totals_are_weighted() -> None:
    report = audit_bars([bar()], windows=[window(count=1), window(count=3, instrument=B)])
    assert report.coverage_ratio == Decimal("0.25")
    assert report.by_instrument[A].coverage_ratio == Decimal(1)
    assert report.by_instrument[B].coverage_ratio == Decimal(0)


def test_different_intervals_in_disjoint_sessions() -> None:
    wide = ValidationWindow(A, T + timedelta(hours=1), T + timedelta(hours=1, minutes=10), 5 * STEP)
    rows = [bar(T), bar(wide.start, end=wide.start + 5 * STEP),
            bar(wide.start + 5 * STEP, end=wide.end)]
    report = audit_bars(rows, windows=[window(count=1), wide])
    assert report.valid and report.expected_bars == report.covered_bars == 3


def test_unsorted_generator_input_keeps_original_issue_indices() -> None:
    original = [bar(T + 2 * STEP), bar(), bar()]
    report = audit_bars((x for x in original), windows=(w for w in [window(count=3)]))
    duplicate = next(x for x in report.issues if x.code is ValidationCode.DUPLICATE_BAR)
    assert duplicate.index == 2
    assert report.missing_timestamps[A] == (T + STEP,)
    assert original[0].start == T + 2 * STEP


def test_equivalent_offsets_match_without_mutating_input() -> None:
    offset = timezone(timedelta(hours=8))
    row = bar(T.astimezone(offset), end=(T + STEP).astimezone(offset))
    report = audit_bars([row], windows=[window(count=1)])
    assert report.valid
    assert row.start.tzinfo is offset


def test_spring_dst_uses_elapsed_time_not_wall_clock_gap() -> None:
    zone = ZoneInfo("America/New_York")
    start = datetime(2025, 3, 9, 1, 59, tzinfo=zone)
    end = datetime(2025, 3, 9, 3, 1, tzinfo=zone)
    w = ValidationWindow(A, start, end, STEP)
    rows = [bar(w.start + i * STEP) for i in range(2)]
    report = audit_bars(rows, windows=[w])
    assert w.expected_bars == 2 and report.valid


def test_fall_dst_distinct_folds_do_not_collapse_to_duplicate() -> None:
    zone = ZoneInfo("America/New_York")
    start = datetime(2025, 11, 2, 1, 0, tzinfo=zone, fold=0)
    end = datetime(2025, 11, 2, 2, 0, tzinfo=zone)
    w = ValidationWindow(A, start, end, STEP)
    rows = []
    for i in range(120):
        instant = w.start + i * STEP
        rows.append(bar(instant.astimezone(zone), end=(instant + STEP).astimezone(zone)))
    report = audit_bars(rows, windows=[w])
    assert report.valid and report.expected_bars == 120 and report.duplicate_bars == 0


def test_coverage_rounding_does_not_depend_on_callers_decimal_context() -> None:
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.traps[Inexact] = True
        report = audit_bars([bar()], windows=[window(count=3)])
        assert report.coverage_ratio == Decimal("0.3333333333333333333333333333")


def test_expansion_limit_fails_before_consuming_bars_not_partial_success() -> None:
    def rows() -> Any:
        pytest.fail("scope limit must precede bar consumption")
        yield bar()
    with pytest.raises(ValueError, match="max_expected_bars"):
        audit_bars(rows(), windows=[window(count=5)], max_expected_bars=4)
    assert audit_bars([], windows=[window(count=5)], max_expected_bars=5).missing_bars == 5


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_expansion_limits(limit: Any) -> None:
    with pytest.raises((TypeError, ValueError)):
        audit_bars([], windows=[window()], max_expected_bars=limit)


def test_per_window_indices_and_missing_timestamps_are_unambiguous() -> None:
    report = audit_bars([], windows=[window(T + 10 * STEP, 1), window(T, 1)])
    assert [i.window_index for i in report.issues] == [0, 1]
    assert report.missing_timestamps[A] == (T, T + 10 * STEP)
    assert [w.window_index for w in report.windows] == [0, 1]


def test_small_grid_exhaustive_presence_invariants() -> None:
    grid = list(range(5))
    for n in range(6):
        for present in combinations(grid, n):
            rows = [bar(T + i * STEP) for i in present]
            for extra in ([], rows[:1]):
                report = audit_bars(rows + extra, windows=[window()])
                assert report.covered_bars + report.missing_bars == 5
                assert report.covered_bars == n
                assert report.observed_bars == n + len(extra)
                assert report.duplicate_bars == len(extra)
                assert set(report.missing_timestamps[A]) == {T + i * STEP for i in set(grid) - set(present)}


def test_legacy_list_api_and_gap_semantics_preserved() -> None:
    rows = [bar(), bar(T + 4 * STEP)]
    result = validate_bars(rows, expected_interval=STEP)
    assert isinstance(result, list)
    assert [i.code for i in result] == [ValidationCode.MISSING_INTERVAL]
    assert validate_bar(bar()) == []


def test_bad_first_duplicate_does_not_hide_later_finite_conflict() -> None:
    rows = [bar(open=Decimal("NaN")), bar(), bar(close=Decimal("100.5"))]
    report = audit_bars(rows, windows=[window(count=1)])
    assert report.count_by_code[ValidationCode.CONFLICTING_DUPLICATE] == 1
    assert report.duplicate_bars == 2 and report.covered_bars == 1
