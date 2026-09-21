"""Canonical bar validation that reports data facts rather than trading opinions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from .models import Bar, InstrumentId


class ValidationCode(str, Enum):
    INVALID_INTERVAL = "invalid_interval"
    UNEXPECTED_DURATION = "unexpected_duration"
    INVALID_OHLC = "invalid_ohlc"
    NEGATIVE_VOLUME = "negative_volume"
    DUPLICATE_BAR = "duplicate_bar"
    MISSING_INTERVAL = "missing_interval"
    NON_FINITE_VALUE = "non_finite_value"
    INVALID_NUMERIC_TYPE = "invalid_numeric_type"
    OUTSIDE_WINDOW = "outside_window"
    MISALIGNED_BAR = "misaligned_bar"
    CONFLICTING_DUPLICATE = "conflicting_duplicate"


class ValidationSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: ValidationCode
    message: str
    index: int | None = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    instrument: InstrumentId | None = None
    window_index: int | None = None
    timestamp: datetime | None = None


def validate_bar(bar: Bar, *, index: int | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if bar.end <= bar.start:
        issues.append(
            ValidationIssue(
                ValidationCode.INVALID_INTERVAL,
                "bar end must be later than bar start",
                index,
            )
        )

    finite: dict[str, Decimal] = {}
    for name in ("open", "high", "low", "close", "volume"):
        value = getattr(bar, name)
        if not isinstance(value, Decimal):
            issues.append(ValidationIssue(ValidationCode.INVALID_NUMERIC_TYPE,
                                          f"{name} must be Decimal; use normalize_bar for coercion", index))
        elif not value.is_finite():
            issues.append(ValidationIssue(ValidationCode.NON_FINITE_VALUE,
                                          f"{name} must be finite", index))
        else:
            finite[name] = value
    if all(name in finite for name in ("open", "high", "low", "close")):
        if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close):
            issues.append(ValidationIssue(ValidationCode.INVALID_OHLC,
                                          "high/low do not contain both open and close", index))
        elif bar.high < bar.low:
            issues.append(ValidationIssue(ValidationCode.INVALID_OHLC,
                                          "high must not be lower than low", index))
    if "volume" in finite and bar.volume < 0:
        issues.append(ValidationIssue(ValidationCode.NEGATIVE_VOLUME,
                                      "volume must not be negative", index))
    return issues


def _duplicate_issues(bars: list[Bar]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen: dict[tuple[InstrumentId, object, object], int] = {}
    for index, bar in enumerate(bars):
        key = (bar.instrument, bar.start, bar.end)
        previous = seen.get(key)
        if previous is not None:
            issues.append(
                ValidationIssue(
                    ValidationCode.DUPLICATE_BAR,
                    f"bar duplicates index {previous}",
                    index,
                )
            )
        else:
            seen[key] = index
    return issues


def _duration_issues(
    bars: list[Bar], expected_interval: timedelta
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, bar in enumerate(bars):
        if bar.end > bar.start and bar.end - bar.start != expected_interval:
            issues.append(
                ValidationIssue(
                    ValidationCode.UNEXPECTED_DURATION,
                    (
                        f"expected bar duration {expected_interval}, "
                        f"got {bar.end - bar.start}"
                    ),
                    index,
                )
            )
    return issues


def _missing_interval_issues(
    bars: list[Bar], expected_interval: timedelta
) -> list[ValidationIssue]:
    by_instrument: dict[InstrumentId, list[tuple[int, Bar]]] = {}
    for index, bar in enumerate(bars):
        by_instrument.setdefault(bar.instrument, []).append((index, bar))

    issues: list[ValidationIssue] = []
    for rows in by_instrument.values():
        rows.sort(key=lambda pair: pair[1].start)
        previous_start = None
        for index, bar in rows:
            if previous_start is not None and bar.start - previous_start > expected_interval:
                expected = previous_start + expected_interval
                issues.append(
                    ValidationIssue(
                        ValidationCode.MISSING_INTERVAL,
                        f"expected next bar at {expected.isoformat()}, got {bar.start.isoformat()}",
                        index,
                    )
                )
            previous_start = bar.start
    return issues


def validate_bars(
    bars: Iterable[Bar], *, expected_interval: timedelta | None = None
) -> list[ValidationIssue]:
    materialized = list(bars)
    issues: list[ValidationIssue] = []
    for index, bar in enumerate(materialized):
        issues.extend(validate_bar(bar, index=index))

    issues.extend(_duplicate_issues(materialized))
    if expected_interval is not None:
        if expected_interval <= timedelta(0):
            raise ValueError("expected_interval must be positive")
        issues.extend(_duration_issues(materialized, expected_interval))
        issues.extend(_missing_interval_issues(materialized, expected_interval))
    return issues
