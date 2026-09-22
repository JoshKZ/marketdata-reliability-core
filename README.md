# Market Data Reliability Core

[![CI](https://github.com/JoshKZ/marketdata-reliability-core/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/JoshKZ/marketdata-reliability-core/actions/workflows/ci.yml)

**Audit market-data CSV files against explicit sessions. Get actionable JSON, not
silently repaired prices.** A provider-independent Python library and offline CLI
for detecting missing bars, duplicates, invalid OHLCV, and time-grid problems
before data reaches research, backtests, or dashboards.

Python 3.11+; Apache-2.0; no third-party runtime dependencies. No API key, brokerage
account, network feed, database, or trading strategy is required.

## Try a complete audit without writing Python

Install from a reviewed repository checkout. This project is not published to
PyPI as part of this release; do not assume an index package of the same name is ours.

```bash
git clone https://github.com/JoshKZ/marketdata-reliability-core.git
cd marketdata-reliability-core
python -m pip install .
python -m marketdata_reliability --bars examples/data/bars_clean.csv --windows examples/data/windows.csv
```

The clean example exits **0** and reports five expected and covered slots with no
findings. Prefer a virtual environment; the [quick start](docs/QUICKSTART.md)
includes Windows PowerShell and Linux commands without shell activation.
Use a published release tag for a stable checkout; `main` can be ahead of releases.

Now try the intentionally broken data:

```bash
python -m marketdata_reliability --bars examples/data/bars_broken.csv --windows examples/data/windows.csv --output report.json
```

This creates a **new** JSON file and intentionally exits **1**. Its summary is:

| Expected slots | Input rows | Covered slots | Missing | Duplicates | Coverage | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| 5 | 5 | 4 | 1 | 1 | 0.8 | 3 |

The errors are one missing bar, one duplicate, and one invalid high. The legal
break between sessions is not reported as a gap. Existing output files are never
overwritten by `--output`; choose a new filename for another run.

`mdr-audit` is the equivalent installed command. Exit **0** means accepted under
the selected policy, **1** means a completed audit with rejected findings, and
**2** means input/configuration/output handling failed. Do not consume an exit-2
output as a completed report. Help/version requests exit 0 without an audit.
The CLI has explicit row, file-size, and expected-grid bounds, not silent truncation.

## Use the library in your own pipeline

```python
from datetime import UTC, datetime, timedelta
from marketdata_reliability import (
    InstrumentId, ValidationWindow, audit_bars, normalize_bar, report_to_json,
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
assert report.expected_bars == 3 and report.covered_bars == 2
assert report.missing_timestamps[instrument] == (start + minute,)
assert not report.valid
print(report_to_json(report))
```

Reports include dataset, instrument, and window summaries; exact missing UTC
starts; original input indices; finding counts; and severity. The versioned JSON
format uses structured instrument identities and decimal-string coverage. It does
not append raw OHLCV values, source payloads, or local file paths.

**Coverage measures presence, not correctness.** Invalid prices can occupy a slot
and still fail validation. Duplicates never improve coverage. Explicit WARNING
overrides do not repair data or erase missing counts. The caller owns session
calendars, price comparability, and whether no-trade intervals should contain bars.

## Existing reliability primitives remain available

- Immutable source observations and replay-safe in-memory ingestion that separates
  duplicate evidence from identity collisions.
- Explicit `BarFieldMap` / `normalize_bar` mapping to canonical OHLCV. Normalization
  accepts Decimal, integers, and decimal strings and rejects floats/non-finite values.
- List-returning validation, deterministic multi-source lineage, supplied historical
  membership checks, and expected-vs-observed historical-correction preconditions.

Correction checks do not atomically write a database. Hashes are not signatures.
Historical membership is only as complete as supplied intervals. Legacy
`validate_bars(expected_interval=...)` remains session-unaware; use `audit_bars`
for declared session coverage. All 28 exports from 0.2.0 remain, with two report
serializers added in 0.3.0. No core identity encoding is silently changed.

## Documentation and contribution

| Start here | Purpose |
| --- | --- |
| [Quick start and CSV contract](docs/QUICKSTART.md) | Installation, input formats, exit codes, policies, and limits. |
| [JSON report contract](docs/JSON_REPORT.md) | Stable report fields, precision, and compatibility. |
| [Audit semantics](docs/AUDIT.md) | Half-open grids, timezones, counts, and missing slots. |
| [Public API](docs/PUBLIC_API.md) | Supported imports and version changes. |
| [Maintenance evidence](docs/MAINTENANCE.md) | Reproducible checks and current project limitations. |
| [Contributing](CONTRIBUTING.md) | Small, synthetic reproductions and contribution workflow. |

This is an early-stage project. Examples and CI are engineering evidence, not
claims of broad adoption. Independent feedback and reproducible issues are welcome;
please remove sensitive data and use the security-reporting route for vulnerabilities.

## Development and distribution verification

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src
python -m pytest
python -m build
python scripts/smoke_distribution.py
```

CI checks Linux Python 3.11/3.12/3.13 and Windows Python 3.13. It builds a source
distribution, builds the wheel from it, then installs into a clean environment
and exercises both CLI entry points and legacy examples outside the source tree.
A successful package-smoke job retains distribution candidates, checksums, and
a synthetic JSON report as a time-limited workflow artifact. Prefer the successful
main workflow matching the reviewed commit; development PR artifacts are candidates.
These artifacts are not PyPI publication or publisher attestations.

## Scope and safety

No data downloading, brokerage login, provider SDK, automatic price repair,
strategy, signal, sizing, execution, or custody belongs in this core. Quote/Trade
models, persistence/recovery orchestration, and market-calendar inference remain
outside this version. Runtime audit processing is offline; source installation
may need network access to obtain build tools.

The CLI is bounded batch processing, not a streaming service or a sandbox for
hostile local filesystems. Output creation is exclusive but not a durable atomic
transaction. Reports still contain instrument identifiers and issue messages;
review them before sharing. Private datasets, production topology, proprietary
vendor material, credentials, and trading-decision IP must not be committed here.

See [SECURITY.md](SECURITY.md) and the [publication boundary](docs/OSS_EXTRACTION_BOUNDARY.md).

## License

Apache License 2.0.
