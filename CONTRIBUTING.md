# Contributing

Thank you for helping improve Market Data Reliability Core.

## Development setup

```bash
git clone https://github.com/JoshKZ/marketdata-reliability-core.git
cd marketdata-reliability-core
python -m venv .venv
python -m pip install -e ".[dev]"
```

Run the local checks before opening a pull request:

```bash
ruff check .
mypy src
pytest
python -m build
```

## Scope

Contributions should strengthen provider-independent reliability: immutable evidence, data quality, provenance, point-in-time semantics, recovery, or safe correction workflows.

Please keep broker/vendor adapters, database integrations, strategy code, and trading execution outside the core unless the repository explicitly adds a public extension boundary for them.

## Pull requests

Prefer small, complete changes with tests that distinguish the new behavior from the old behavior. Describe:

- the reliability problem;
- the invariant or contract being changed;
- the test evidence;
- any compatibility impact.

Do not weaken a validation or safety invariant merely to make a test pass.

## Data and secrets

Use synthetic fixtures or data you are legally allowed to redistribute. Never attach credentials, private market-data entitlements, proprietary SDK material, account state, or production database exports to issues or pull requests.

See `docs/OSS_EXTRACTION_BOUNDARY.md` for the repository's public/private boundary.
