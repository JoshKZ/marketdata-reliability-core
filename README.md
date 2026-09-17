# Market Data Reliability Core

Provider-agnostic reliability primitives for financial market data.

Market-data pipelines usually fail in boring ways: duplicate observations, missing bars, silent source rewrites, ambiguous corrections, present-day universes leaking into historical tests, and provider-specific fields escaping into downstream research. This project focuses on those reliability problems before data reaches a backtest, model, dashboard, or trading system.

## What it provides

The first public core is intentionally small:

- **Immutable source observations** with deterministic fingerprints.
- **Idempotent ingestion** that distinguishes replayed observations from collisions.
- **Canonical bar models** independent of any broker or data vendor.
- **Data-quality validation** for OHLC consistency, negative volume, duplicates, and missing intervals.
- **Point-in-time universe semantics** to help prevent survivorship bias.
- **Safe historical-correction preconditions** that require expected-vs-observed agreement before a caller applies a change.
- **Provenance-friendly identifiers** so downstream records can retain their source lineage.

The library does **not** download market data, place orders, implement signals, provide a backtesting engine, or embed a production database schema.

## Status

`0.1.0a0` is an early public foundation. APIs may change before the first stable release.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
pytest
```

A minimal validation example:

```python
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from marketdata_reliability import Bar, InstrumentId, validate_bars

utc = timezone.utc
instrument = InstrumentId(market="XNAS", symbol="DEMO", asset_class="equity")
bar = Bar(
    instrument=instrument,
    start=datetime(2026, 1, 2, 14, 30, tzinfo=utc),
    end=datetime(2026, 1, 2, 14, 31, tzinfo=utc),
    open=Decimal("100"),
    high=Decimal("101"),
    low=Decimal("99"),
    close=Decimal("100.5"),
    volume=Decimal("1200"),
)

assert validate_bars([bar], expected_interval=timedelta(minutes=1)) == []
```

To see the validator catch intentionally broken data:

```bash
python examples/validate_broken_bars.py
```

## Reliability model

The intended flow is:

```text
provider / file / feed
        |
        v
immutable SourceObservation
        |
        v
normalization performed by caller / adapter
        |
        v
canonical Bar or other domain record
        |
        +----> validation
        |
        +----> provenance / lineage retained downstream
        |
        +----> point-in-time membership checks
        |
        +----> correction preconditions when history must change
```

A repeated ingestion should be safe when it replays the same immutable observation. A historical correction should never be authorized merely because a caller asks for a new value; the current observed value must still match the proposal's expected value.

## Design principles

1. **Raw evidence is immutable.** Fix history with explicit correction records rather than silently rewriting source observations.
2. **Provider code stays at the edge.** The core does not depend on a broker SDK, exchange SDK, proprietary binary, or vendor field naming convention.
3. **Time is part of identity.** Market/event time and observation time are distinct concepts and must be timezone-aware.
4. **Point-in-time truth beats today's convenience.** Current listings are not a valid historical universe.
5. **Idempotency is mechanical.** Re-running a pipeline should not create silent duplicates.
6. **Validation reports facts, not trading opinions.** No alpha, signal, position, or execution logic belongs here.

## Non-goals

The core deliberately excludes:

- brokerage or exchange login flows;
- proprietary SDK code or copied vendor documentation;
- order submission, cancellation, portfolio, or account functionality;
- strategy, factor, alpha, ranking, sizing, or arbitrage logic;
- production connection strings or production database topology;
- a universal market-calendar implementation;
- a full event store or backtesting engine.

## Repository safety boundary

Public-source extraction rules are documented in [`docs/OSS_EXTRACTION_BOUNDARY.md`](docs/OSS_EXTRACTION_BOUNDARY.md). In short: generic reliability concepts are welcome; credentials, proprietary material, production topology, private data, and trading decision logic are not.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src
pytest
python -m build
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for contribution guidelines and [`SECURITY.md`](SECURITY.md) for security reporting.

## License

Apache License 2.0.
