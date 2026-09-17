# Repository Instructions

Market Data Reliability Core is a public, provider-independent Python library. Keep changes small, testable, and usable without private infrastructure.

## Core invariants

- Source observations are immutable evidence; corrections do not rewrite source evidence.
- Provider/vendor details stay at the edge and must not become canonical truth.
- Event/market time and observation time are distinct and timezone-aware.
- Replays are idempotent; an identity collision with different evidence fails loudly.
- Historical universe membership is point-in-time, not reconstructed from today's listings.
- Historical correction requires explicit evidence plus expected-vs-observed verification before a persistence layer writes.
- Validation reports data-quality facts only. Do not add trading signals, strategy decisions, execution logic, positions, or alpha.

## Public-repository safety

Read `docs/OSS_EXTRACTION_BOUNDARY.md` before adapting ideas from any private or production code. Never commit secrets, proprietary SDK material, private datasets, production topology, or trading-decision IP.

## Engineering workflow

For behavior changes, add or update tests that mechanically prove the contract. Run:

```bash
ruff check .
mypy src
pytest
python -m build
```

Do not add a framework, dependency, persistence layer, or provider adapter unless a concrete public use case requires it and the existing core is insufficient.
