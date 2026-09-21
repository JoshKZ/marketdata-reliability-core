# Market Data Reliability Core

Provider-agnostic reliability primitives for financial market data.

Validate market-data evidence before it reaches research, backtests, or dashboards.
The library provides source observations, normalization, validation, lineage,
historical membership, and correction precondition checks without a vendor SDK
or trading decision logic. Runtime dependencies: Python's standard library only.

## New in 0.2.0: session-aware dataset audit

Declare the windows in which bars should exist. Audit missing slots, duplicates,
OHLCV problems, duration, and alignment without treating lunch breaks or overnight
closures as missing data. The caller owns the trading calendar.

```python
from datetime import UTC, datetime, timedelta
from marketdata_reliability import (
    InstrumentId, ValidationWindow, audit_bars, normalize_bar,
)

instrument = InstrumentId("SYNTH", "DEMO", "equity")
start = datetime(2026, 1, 2, 9, tzinfo=UTC)
minute = timedelta(minutes=1)
window = ValidationWindow(instrument, start, start + 3 * minute, minute)
rows = [
    normalize_bar(
        {"open": "100", "high": "101", "low": "99", "close": "100.5", "volume": 10},
        instrument=instrument, start=start + i * minute, end=start + (i + 1) * minute,
    )
    for i in (0, 2)
]
report = audit_bars(rows, windows=[window])
assert report.expected_bars == 3
assert report.covered_bars == 2
assert report.missing_timestamps[instrument] == (start + minute,)
assert not report.valid
```

`report.windows` and `report.by_instrument` expose per-window and per-instrument
summaries. `count_by_code`, `error_count`, and `warning_count` support pipeline
checks. Missing timestamps are UTC bar starts keyed by instrument.

**Coverage measures presence, not correctness.** A bar with invalid OHLCV can
occupy its expected slot and still fail validation. Duplicates do not increase
coverage. `valid` means no ERROR remains under the chosen policy; explicit WARNING
overrides do not repair the data or erase missing counts.

See [the audit contract](docs/AUDIT.md) for half-open boundaries, dense-grid
assumptions, severity policy, timezones, and resource limits.

## Installation and offline examples

Requires Python 3.11+. Install from this repository; this guide does not assume
that a package has been published to PyPI.

```bash
git clone https://github.com/JoshKZ/marketdata-reliability-core.git
cd marketdata-reliability-core
python -m pip install .
python examples/audit_two_sessions.py
python examples/validate_broken_bars.py
```

The two-session example is entirely synthetic and asserts its output: 10 expected
slots, 9 input rows, 8 covered slots, 2 missing, 1 duplicate, and 4 errors including
one invalid high. It needs no account, network feed, database, or API key.

For development, use a virtual environment and install the development extras:

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest
python -m build
```

CI runs lint, strict type checking, all tests, and builds on Python 3.11, 3.12,
and 3.13. It also installs a wheel into a fresh environment and runs the legacy
normalization path and the new session-audit example using isolated Python.

## Existing core capabilities

- **Source observations** with deterministic fingerprints and replay-safe
  in-memory ingestion that distinguishes duplicates from identity collisions.
- **Explicit normalization** using `BarFieldMap` and `normalize_bar` to translate
  provider-shaped mappings into canonical OHLCV bars. Numeric inputs accept
  Decimal, integers, and decimal strings; binary floats and non-finite values
  are rejected. Timestamp parsing remains the caller's responsibility.
- **Validation and provenance:** the existing list-returning `validate_bar` and
  `validate_bars` APIs, plus deterministic multi-source lineage records.
- **Historical membership and correction preconditions:** `members_at` checks
  supplied historical intervals; `verify_correction` checks expected versus
  observed values. It does not persist or atomically apply a correction.

The package-root import surface is documented in [PUBLIC_API.md](docs/PUBLIC_API.md).
The 0.2.0 surface preserves all 0.1.0 exported names and adds six audit names.
`validate_bars(expected_interval=...)` remains calendar-unaware; use `audit_bars`
for explicitly scoped session coverage. Added optional `ValidationIssue` fields
are documented for consumers that serialize dataclasses.

## Scope and safety

The core does not download market data, place orders, select instruments, generate
signals, or provide a backtesting engine. It does not infer exchange calendars,
choose a preferred provider, silently repair data, or decide which price is true.
Audit windows must describe a comparable dense bar series, including the caller's
no-trade-bar policy. Historical membership is only as complete as supplied records.

Proprietary SDK material, credentials, private datasets, production topology, and
trading strategies stay outside this repository. Checkpoint/recovery orchestration,
provider adapters, real-time Quote/Trade models, and PyPI publishing are not part
of this version.

See [OSS_EXTRACTION_BOUNDARY.md](docs/OSS_EXTRACTION_BOUNDARY.md),
[CONTRIBUTING.md](CONTRIBUTING.md), and [SECURITY.md](SECURITY.md).

## License

Apache License 2.0.
