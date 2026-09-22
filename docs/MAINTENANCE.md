# Maintenance and public evidence

## Purpose and current stage

Market Data Reliability Core provides reusable checks between market-data
collection and downstream research, backtests, and dashboards. The shared problem
is not choosing profitable trades: it is detecting duplicated, missing,
misaligned, non-finite, or ambiguously corrected evidence before users depend on it.
The core is provider-independent and runs without a proprietary SDK or database.

This is an early-stage project. Reproducible examples and maintenance history are
engineering evidence, not proof of broad external adoption. No external download,
star, institutional-use, or user-count claims are made in this document. PyPI
publication is a separate future step; no package-index adoption is asserted.

## Reproduce the evidence

| Claim | Public evidence |
| --- | --- |
| Session-aware coverage, duplicates, timezone boundaries | `tests/test_audit.py`, `docs/AUDIT.md` |
| Strict CSV failure handling and no-overwrite output | `tests/test_cli.py`, `docs/QUICKSTART.md` |
| Detached, versioned JSON reports | `tests/test_reporting.py`, `docs/JSON_REPORT.md` |
| Preserved prior exports | `tests/test_public_api.py` |
| Installed distribution works outside the checkout | `scripts/smoke_distribution.py` |
| No runtime third-party dependency | `pyproject.toml` and no-dependency wheel installation in CI |
| Publication scope and contributor boundaries | `AGENTS.md`, `docs/OSS_EXTRACTION_BOUNDARY.md`, `SECURITY.md` |

Run `python -m pip install -e ".[dev]"`, `ruff check .`, `mypy src`,
`python -m pytest`, `python -m build`, and `python scripts/smoke_distribution.py`.
Use fresh build output before the distribution smoke check.
GitHub Actions verifies Linux Python 3.11/3.12/3.13 and Windows Python 3.13.
Always inspect the workflow result for the specific commit, not just a badge.
The source distribution includes documentation, tests, and synthetic fixtures.

## Maintenance approach

Changes use regression tests, review, pull requests, and CI before main-branch
integration. Agent-assisted implementation and same-agent review are not an
independent external security audit. The project benefits from independent bug
reports, review, and small reproducible contributions. Report vulnerabilities
through the route in SECURITY.md and keep private datasets out of public issues.

Release progress is tracked in issues and release notes; a package version in
source does not itself mean that a GitHub tag or PyPI package was published.
Development branch artifacts are candidates. Prefer artifacts from the successful
main workflow matching the reviewed commit. CI artifacts expire; source tags and
release notes remain the release reference. Checksums detect file mismatch but
are not cryptographic publisher attestations.

## Next priorities

1. Obtain real external feedback on CSV/report integration and usability.
2. Address demonstrated correctness and performance gaps with regression evidence.
3. Configure a maintainer-controlled Trusted Publisher before any PyPI publication.

Do not add broker integration, quote models, recovery orchestration, or AI-based
correctness merely to increase the feature count. New dependencies and interfaces
need a concrete public use case. Existing hashing and provenance primitives are
not cryptographic authentication, and require a separate compatibility-aware
review before their identity encoding is changed.
