"""Versioned, JSON-safe projections of completed audits (not raw market data)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from .audit import InstrumentReport, ValidationReport, WindowReport
from .models import InstrumentId
from .validation import ValidationIssue


def _instrument(value: InstrumentId | None) -> dict[str, str] | None:
    if value is None:
        return None
    # Never use delimiter-joined identities as JSON keys.
    return {"market": value.market, "symbol": value.symbol, "asset_class": value.asset_class}


def _timestamp(value: datetime | None) -> str | None:
    return None if value is None else value.astimezone(UTC).isoformat(timespec="microseconds")


def _summary(value: ValidationReport | InstrumentReport | WindowReport) -> dict[str, object]:
    ratio = value.coverage_ratio
    return {
        "expected_bars": value.expected_bars,
        "observed_bars": value.observed_bars,
        "covered_bars": value.covered_bars,
        "missing_bars": value.missing_bars,
        "duplicate_bars": value.duplicate_bars,
        "coverage_ratio": None if ratio is None else str(ratio),
        "valid": value.valid,
        "issue_count": value.issue_count,
        "error_count": value.error_count,
        "warning_count": value.warning_count,
        "count_by_code": {code.value: count for code, count in value.count_by_code.items()},
    }


def _issue(value: ValidationIssue) -> dict[str, object]:
    return {
        "code": value.code.value,
        "severity": value.severity.value,
        "message": value.message,
        "index": value.index,
        "instrument": _instrument(value.instrument),
        "window_index": value.window_index,
        "timestamp": _timestamp(value.timestamp),
    }


def report_to_dict(report: ValidationReport) -> dict[str, object]:
    """Return a detached JSON-compatible audit document using schema version 1.0.

    Coverage is serialized as a decimal string (or null), timestamps as UTC ISO
    strings, and identities as objects. Findings appear once at dataset level;
    window/instrument summaries refer to the same input and window indices.
    No clock, file path, raw price, credential, or source payload is added.
    This is serialization, not authentication or a revalidation of the report.
    """
    if not isinstance(report, ValidationReport):
        raise TypeError("report must be ValidationReport")
    windows: list[dict[str, object]] = []
    for item in report.windows:
        windows.append({
            "window_index": item.window_index,
            "instrument": _instrument(item.window.instrument),
            "start": _timestamp(item.window.start),
            "end": _timestamp(item.window.end),
            "interval_microseconds": item.window.expected_interval // timedelta(microseconds=1),
            "summary": _summary(item),
            "missing_timestamps": [_timestamp(t) for t in item.missing_timestamps],
        })
    instruments: list[dict[str, object]] = []
    for item in sorted(report.instruments, key=lambda entry: entry.instrument):
        instruments.append({
            "instrument": _instrument(item.instrument),
            "summary": _summary(item),
            "outside_window_bars": item.outside_window_bars,
            "window_indices": [window.window_index for window in item.windows],
        })
    return {
        "schema_version": "1.0",
        "report_type": "marketdata-reliability/audit",
        "coverage_basis": "presence_not_validity",
        "summary": _summary(report),
        "outside_window_bars": report.outside_window_bars,
        "issues": [_issue(issue) for issue in report.issues],
        "windows": windows,
        "instruments": instruments,
    }


def report_to_json(report: ValidationReport, *, indent: int | None = 2) -> str:
    """Serialize deterministically for a fixed report, preserving input issue order.

    ASCII escaping keeps Unicode and terminal control characters inert in JSON.
    No trailing newline is added. Schema version is separate from package version.
    """
    if indent is not None and (type(indent) is not int or not 0 <= indent <= 8):
        raise ValueError("indent must be None or an integer between 0 and 8")
    return json.dumps(report_to_dict(report), ensure_ascii=True, allow_nan=False,
                      sort_keys=True, indent=indent)
