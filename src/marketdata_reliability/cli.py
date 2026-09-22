"""Offline, bounded CSV audit command; no network, repair, or provider integration."""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections.abc import Iterator, Sequence
from datetime import datetime, timedelta
from decimal import Context, Decimal, InvalidOperation, localcontext
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .audit import ValidationWindow, audit_bars
from .models import Bar, InstrumentId
from .reporting import report_to_json
from .validation import ValidationCode, ValidationSeverity

_ID = ("market", "symbol", "asset_class")
_BAR_COLUMNS = (*_ID, "start", "end", "open", "high", "low", "close", "volume")
_WINDOW_COLUMNS = (*_ID, "start", "end", "interval_seconds")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


class _InputError(ValueError):
    """Invalid input; messages never include user-supplied cell contents."""


def _positive(value: str) -> int:
    if not re.fullmatch(r"[0-9]{1,12}", value) or int(value) <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer of at most 12 digits")
    return int(value)


def _rows(path: Path, columns: tuple[str, ...], label: str,
          max_rows: int, max_file_bytes: int) -> Iterator[tuple[int, dict[str, str]]]:
    try:
        if not path.is_file():
            raise _InputError(f"{label}: expected a regular local file")
        if path.stat().st_size > max_file_bytes:
            raise _InputError(f"{label}: exceeds max-file-bytes")
        with path.open("rb") as handle:
            data = handle.read(max_file_bytes + 1)
    except OSError as exc:
        raise _InputError(f"{label}: cannot read input file") from exc
    if len(data) > max_file_bytes:
        raise _InputError(f"{label}: exceeds max-file-bytes")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise _InputError(f"{label}: input must be UTF-8 (BOM is allowed)") from exc
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, None)
        if header is None or len(header) != len(columns) or set(header) != set(columns):
            raise _InputError(f"{label}: columns must appear exactly once: {','.join(columns)}")
        for number, cells in enumerate(reader, start=1):
            if number > max_rows:
                raise _InputError(f"{label}: exceeds max-rows")
            if len(cells) != len(header):
                raise _InputError(f"{label}: record {number}: wrong number of columns")
            if any(len(cell) > 4096 or "\x00" in cell for cell in cells):
                raise _InputError(f"{label}: record {number}: NUL or oversized cell")
            yield number, dict(zip(header, cells))
    except csv.Error as exc:
        raise _InputError(f"{label}: malformed CSV near physical line {reader.line_num}") from exc


def _identity(row: dict[str, str], where: str) -> InstrumentId:
    for field in _ID:
        value = row[field]
        if (not value or value != value.strip()
                or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise _InputError(f"{where}: invalid {field}")
    return InstrumentId(row["market"], row["symbol"], row["asset_class"])


def _instant(value: str, where: str, field: str) -> datetime:
    if not _TIMESTAMP.fullmatch(value) or value.endswith("-00:00"):
        raise _InputError(f"{where}: {field} requires an ISO timestamp with an explicit offset")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise _InputError(f"{where}: invalid {field} timestamp") from exc


def _number(value: str, where: str, field: str) -> Decimal:
    if not value or len(value) > 128 or value != value.strip():
        raise _InputError(f"{where}: invalid {field} decimal")
    try:
        # Construction is exact; malformed syntax fails regardless of caller traps.
        with localcontext(Context(traps=[InvalidOperation])):
            return Decimal(value)
    except InvalidOperation as exc:
        raise _InputError(f"{where}: invalid {field} decimal") from exc


def _bars(path: Path, max_rows: int, max_file_bytes: int) -> Iterator[Bar]:
    for number, row in _rows(path, _BAR_COLUMNS, "bars", max_rows, max_file_bytes):
        where = f"bars: record {number}"
        yield Bar(
            instrument=_identity(row, where),
            start=_instant(row["start"], where, "start"),
            end=_instant(row["end"], where, "end"),
            open=_number(row["open"], where, "open"),
            high=_number(row["high"], where, "high"),
            low=_number(row["low"], where, "low"),
            close=_number(row["close"], where, "close"),
            volume=_number(row["volume"], where, "volume"),
        )


def _windows(path: Path, max_rows: int, max_file_bytes: int) -> Iterator[ValidationWindow]:
    for number, row in _rows(path, _WINDOW_COLUMNS, "windows", max_rows, max_file_bytes):
        where = f"windows: record {number}"
        seconds = row["interval_seconds"]
        if not re.fullmatch(r"[0-9]{1,12}", seconds) or int(seconds) <= 0:
            raise _InputError(f"{where}: interval_seconds must be a positive integer")
        try:
            yield ValidationWindow(
                _identity(row, where), _instant(row["start"], where, "start"),
                _instant(row["end"], where, "end"), timedelta(seconds=int(seconds)),
            )
        except (ValueError, OverflowError) as exc:
            raise _InputError(f"{where}: invalid window identity, timestamps, or interval") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdr-audit", allow_abbrev=False,
        description="Audit local OHLCV CSV against explicit sessions; no network or data repair.",
    )
    try:
        package_version = version("marketdata-reliability-core")
    except PackageNotFoundError:
        package_version = "uninstalled"
    parser.add_argument("--version", action="version", version=f"%(prog)s {package_version}")
    parser.add_argument("--bars", type=Path, required=True, help="UTF-8 OHLCV CSV")
    parser.add_argument("--windows", type=Path, required=True, help="UTF-8 expected-window CSV")
    parser.add_argument("--output", type=Path, help="create a NEW JSON file; never overwrite")
    parser.add_argument("--max-rows", type=_positive, default=100_000, help="per input file (100000)")
    parser.add_argument("--max-file-bytes", type=_positive, default=16_777_216,
                        help="per input file (16777216)")
    parser.add_argument("--max-expected-bars", type=_positive, default=100_000,
                        help="expected grid slots (100000)")
    parser.add_argument("--warn", action="append", default=[],
                        choices=[code.value for code in ValidationCode], metavar="CODE",
                        help="explicitly downgrade a finding code to WARNING; repeatable")
    parser.add_argument("--warnings-as-errors", action="store_true",
                        help="exit 1 for warning-only reports too; report severities stay unchanged")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Exit 0: accepted; 1: completed with rejected findings; 2: not completed.

    No output file is opened until parsing, auditing, and serialization all succeed.
    Standard output contains only JSON (unless help/version was requested).
    """
    args = _parser().parse_args(argv)
    try:
        windows = tuple(_windows(args.windows, args.max_rows, args.max_file_bytes))
        policy = {ValidationCode(code): ValidationSeverity.WARNING for code in args.warn}
        report = audit_bars(
            _bars(args.bars, args.max_rows, args.max_file_bytes), windows=windows,
            severity_overrides=policy, max_expected_bars=args.max_expected_bars,
        )
        text = report_to_json(report) + "\n"
        if args.output is None:
            sys.stdout.write(text)
            sys.stdout.flush()
        else:
            # Exclusive creation also rejects existing input paths and links.
            with args.output.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
    except _InputError as exc:
        print(f"mdr-audit: {exc}", file=sys.stderr)
        return 2
    except (ValueError, OverflowError):
        print("mdr-audit: invalid audit scope or timestamps; check windows and limits", file=sys.stderr)
        return 2
    except OSError:
        print("mdr-audit: cannot write report; output must be new and destination writable", file=sys.stderr)
        return 2
    return int(not report.valid or (args.warnings_as_errors and report.warning_count > 0))
