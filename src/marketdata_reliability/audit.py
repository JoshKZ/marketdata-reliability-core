"""Dataset audits against caller-declared, half-open expected bar windows."""

from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from types import MappingProxyType

from .models import Bar, InstrumentId, _require_aware
from .validation import ValidationCode, ValidationIssue, ValidationSeverity, validate_bar


@dataclass(frozen=True, slots=True)
class ValidationWindow:
    """A dense, start-labelled bar grid in [start, end); stored in UTC.

    The caller owns calendar, halt, and no-trade-bar policy. Duration must be an
    exact positive multiple of expected_interval. No partial final bar is inferred.
    """

    instrument: InstrumentId
    start: datetime
    end: datetime
    expected_interval: timedelta

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, InstrumentId):
            raise TypeError("instrument must be InstrumentId")
        for name in ("start", "end"):
            value = getattr(self, name)
            if not isinstance(value, datetime):
                raise TypeError(f"{name} must be datetime")
            _require_aware(value, name)
            object.__setattr__(self, name, value.astimezone(UTC))
        if not isinstance(self.expected_interval, timedelta):
            raise TypeError("expected_interval must be timedelta")
        if self.expected_interval <= timedelta(0):
            raise ValueError("expected_interval must be positive")
        duration = self.end - self.start
        if duration <= timedelta(0):
            raise ValueError("window end must be later than start")
        if duration % self.expected_interval:
            raise ValueError("window duration must be a multiple of expected_interval")

    @property
    def expected_bars(self) -> int:
        return (self.end - self.start) // self.expected_interval


@dataclass(frozen=True, slots=True)
class _Summary:
    expected_bars: int
    observed_bars: int
    covered_bars: int
    duplicate_bars: int
    issues: tuple[ValidationIssue, ...]

    def __post_init__(self) -> None:
        for value in (self.expected_bars, self.observed_bars, self.covered_bars, self.duplicate_bars):
            if type(value) is not int or value < 0:
                raise ValueError("summary counts must be non-negative integers")
        if self.covered_bars > min(self.expected_bars, self.observed_bars):
            raise ValueError("covered_bars exceeds expected or observed count")
        if self.duplicate_bars > self.observed_bars:
            raise ValueError("duplicate_bars exceeds observed count")
        object.__setattr__(self, "issues", tuple(self.issues))

    @property
    def missing_bars(self) -> int:
        return self.expected_bars - self.covered_bars

    @property
    def coverage_ratio(self) -> Decimal | None:
        """Presence, not validity; None for an undeclared instrument (zero denominator)."""
        if not self.expected_bars:
            return None
        # Do not inherit a caller's precision, rounding, or Inexact trap settings.
        with localcontext(Context(prec=28, rounding=ROUND_HALF_EVEN, traps=[])):
            return Decimal(self.covered_bars) / Decimal(self.expected_bars)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def count_by_code(self) -> Mapping[ValidationCode, int]:
        return MappingProxyType(dict(Counter(issue.code for issue in self.issues)))

    @property
    def error_count(self) -> int:
        return sum(issue.severity is ValidationSeverity.ERROR for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity is ValidationSeverity.WARNING for issue in self.issues)

    @property
    def valid(self) -> bool:
        """True exactly when no ERROR remains under the selected severity policy."""
        return self.error_count == 0


@dataclass(frozen=True, slots=True)
class WindowReport(_Summary):
    window_index: int
    window: ValidationWindow
    missing_timestamps: tuple[datetime, ...]

    def __post_init__(self) -> None:
        _Summary.__post_init__(self)
        object.__setattr__(self, "missing_timestamps", tuple(self.missing_timestamps))


@dataclass(frozen=True, slots=True)
class InstrumentReport(_Summary):
    instrument: InstrumentId
    windows: tuple[WindowReport, ...]
    outside_window_bars: int

    def __post_init__(self) -> None:
        _Summary.__post_init__(self)
        object.__setattr__(self, "windows", tuple(self.windows))

    @property
    def missing_timestamps(self) -> tuple[datetime, ...]:
        return tuple(sorted(t for w in self.windows for t in w.missing_timestamps))


@dataclass(frozen=True, slots=True)
class ValidationReport(_Summary):
    """Immutable audit result; use counts and issues together, not coverage alone."""

    windows: tuple[WindowReport, ...]
    instruments: tuple[InstrumentReport, ...]
    outside_window_bars: int

    def __post_init__(self) -> None:
        _Summary.__post_init__(self)
        object.__setattr__(self, "windows", tuple(self.windows))
        object.__setattr__(self, "instruments", tuple(self.instruments))

    @property
    def by_instrument(self) -> Mapping[InstrumentId, InstrumentReport]:
        return MappingProxyType({item.instrument: item for item in self.instruments})

    @property
    def missing_timestamps(self) -> Mapping[InstrumentId, tuple[datetime, ...]]:
        """UTC start timestamps keyed by instrument; never mix instruments silently."""
        return MappingProxyType({item.instrument: item.missing_timestamps for item in self.instruments})


@dataclass
class _WindowState:
    observed: int = 0
    duplicates: int = 0
    covered: set[datetime] = field(default_factory=set)
    issues: list[ValidationIssue] = field(default_factory=list)


def _window_index(
    windows: tuple[ValidationWindow, ...], max_expected_bars: int,
) -> dict[InstrumentId, list[tuple[datetime, int]]]:
    if type(max_expected_bars) is not int or max_expected_bars <= 0:
        raise ValueError("max_expected_bars must be a positive integer")
    if not windows:
        raise ValueError("at least one validation window is required")
    by_instrument: dict[InstrumentId, list[tuple[datetime, int]]] = defaultdict(list)
    total = 0
    for index, window in enumerate(windows):
        if not isinstance(window, ValidationWindow):
            raise TypeError("windows must contain ValidationWindow objects")
        total += window.expected_bars
        if total > max_expected_bars:
            raise ValueError("scope exceeds max_expected_bars; split the audit or raise the limit")
        by_instrument[window.instrument].append((window.start, index))
    for entries in by_instrument.values():
        entries.sort()
        for (_, previous), (_, current) in zip(entries, entries[1:]):
            if windows[current].start < windows[previous].end:
                raise ValueError("windows for the same instrument must not overlap")
    return by_instrument


def _prices(bar: Bar) -> tuple[Decimal, ...] | None:
    values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
    if all(isinstance(value, Decimal) and value.is_finite() for value in values):
        return values
    return None


def audit_bars(
    bars: Iterable[Bar],
    *,
    windows: Iterable[ValidationWindow],
    severity_overrides: Mapping[ValidationCode, ValidationSeverity] | None = None,
    max_expected_bars: int = 1_000_000,
) -> ValidationReport:
    """Audit dense bar grids without downloading data or guessing exchange calendars.

    Counts distinguish raw input rows from uniquely covered exact (start, end)
    slots. Numerically invalid but correctly located bars count as present and
    still emit errors. Duplicates never increase coverage. Out-of-scope rows are
    reported, not dropped. Bad scope/policy raises before consuming input bars.

    All comparisons use UTC elapsed time. Input order is retained in issue.index;
    window_index refers to the supplied window order. The explicit expansion
    limit bounds expected-grid/missing-timestamp materialization, not input rows.
    """
    declared = tuple(windows)
    lookup = _window_index(declared, max_expected_bars)
    policy = dict(severity_overrides) if severity_overrides is not None else {}
    if any(not isinstance(k, ValidationCode) or not isinstance(v, ValidationSeverity)
           for k, v in policy.items()):
        raise TypeError("severity_overrides must map ValidationCode to ValidationSeverity")
    states = [_WindowState() for _ in declared]
    issues: list[ValidationIssue] = []
    instrument_issues: dict[InstrumentId, list[ValidationIssue]] = defaultdict(list)
    observed: Counter[InstrumentId] = Counter()
    duplicates: Counter[InstrumentId] = Counter()
    outside: Counter[InstrumentId] = Counter()
    seen: dict[tuple[InstrumentId, datetime, datetime], tuple[int, tuple[Decimal, ...] | None]] = {}

    def emit(issue: ValidationIssue, instrument: InstrumentId, wi: int | None, t: datetime) -> None:
        annotated = replace(issue, severity=policy.get(issue.code, ValidationSeverity.ERROR),
                            instrument=instrument, window_index=wi, timestamp=t)
        issues.append(annotated)
        instrument_issues[instrument].append(annotated)
        if wi is not None:
            states[wi].issues.append(annotated)

    for index, original in enumerate(bars):
        if not isinstance(original, Bar):
            raise TypeError("bars must contain Bar objects")
        # Work on a copy: same-zone datetime comparisons otherwise ignore fold.
        bar = replace(original, start=original.start.astimezone(UTC), end=original.end.astimezone(UTC))
        instrument = bar.instrument
        observed[instrument] += 1
        entries = lookup.get(instrument, [])
        position = bisect_right(entries, (bar.start, len(declared))) - 1
        wi: int | None = None
        if position >= 0:
            candidate = entries[position][1]
            if bar.start < declared[candidate].end:
                wi = candidate
        for issue in validate_bar(bar, index=index):
            emit(issue, instrument, wi, bar.start)
        key = (instrument, bar.start, bar.end)
        previous = seen.get(key)
        prices = _prices(bar)
        if previous is not None:
            duplicates[instrument] += 1
            if wi is not None:
                states[wi].duplicates += 1
            emit(ValidationIssue(ValidationCode.DUPLICATE_BAR,
                                 f"bar duplicates index {previous[0]}", index), instrument, wi, bar.start)
            if previous[1] is not None and prices is not None and previous[1] != prices:
                emit(ValidationIssue(ValidationCode.CONFLICTING_DUPLICATE,
                                     f"conflicting OHLCV in duplicate group starting at index {previous[0]}", index), instrument, wi, bar.start)
            elif previous[1] is None and prices is not None:
                seen[key] = (previous[0], prices)
        else:
            seen[key] = (index, prices)
        if wi is None:
            outside[instrument] += 1
            emit(ValidationIssue(ValidationCode.OUTSIDE_WINDOW,
                                 "bar start is outside declared windows", index), instrument, None, bar.start)
            continue
        state, window = states[wi], declared[wi]
        state.observed += 1
        duration = bar.end - bar.start
        if duration > timedelta(0) and duration != window.expected_interval:
            emit(ValidationIssue(ValidationCode.UNEXPECTED_DURATION,
                                 f"expected duration {window.expected_interval}, got {duration}", index),
                 instrument, wi, bar.start)
        if ((bar.start - window.start) % window.expected_interval == timedelta(0)
                and duration == window.expected_interval and bar.end <= window.end):
            state.covered.add(bar.start)
        else:
            emit(ValidationIssue(ValidationCode.MISALIGNED_BAR,
                                 "bar does not occupy an exact expected window slot", index),
                 instrument, wi, bar.start)

    window_reports: list[WindowReport] = []
    for wi, (window, state) in enumerate(zip(declared, states)):
        missing = tuple(t for slot in range(window.expected_bars)
                        if (t := window.start + slot * window.expected_interval) not in state.covered)
        for t in missing:
            emit(ValidationIssue(ValidationCode.MISSING_INTERVAL,
                                 f"missing expected bar at {t.isoformat()}"), window.instrument, wi, t)
        window_reports.append(WindowReport(window.expected_bars, state.observed, len(state.covered),
                                           state.duplicates, tuple(state.issues), wi, window, missing))
    grouped: dict[InstrumentId, list[WindowReport]] = defaultdict(list)
    for item in window_reports:
        grouped[item.window.instrument].append(item)
    instrument_reports = tuple(
        InstrumentReport(
            sum(w.expected_bars for w in grouped[instrument]), observed[instrument],
            sum(w.covered_bars for w in grouped[instrument]), duplicates[instrument],
            tuple(instrument_issues[instrument]), instrument, tuple(grouped[instrument]), outside[instrument],
        )
        for instrument in sorted(set(lookup) | set(observed))
    )
    return ValidationReport(
        sum(w.expected_bars for w in declared), sum(observed.values()),
        sum(len(state.covered) for state in states), sum(duplicates.values()),
        tuple(issues), tuple(window_reports), instrument_reports, sum(outside.values()),
    )
