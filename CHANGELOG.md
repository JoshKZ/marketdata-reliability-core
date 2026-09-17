# Changelog

All notable changes will be documented in this file.

## Unreleased

## 0.1.0 - 2026-09-17

### Added

- Immutable source observations with deterministic fingerprints and replay-safe ingestion semantics.
- Provider-independent canonical OHLCV bars and explicit provider-field normalization.
- Safe decimal coercion that rejects binary floats and non-finite canonical values.
- Data-quality validation for OHLC consistency, negative volume, duplicates, missing intervals, invalid intervals, and unexpected bar duration.
- Point-in-time universe membership primitives to reduce survivorship-bias leakage.
- Deterministic multi-source lineage records for derived market-data records.
- Historical-correction precondition verification using expected-vs-observed checks.
- Edge-case coverage for timezone awareness, deterministic observation fingerprints, collision behavior, lineage identity, normalization failures, correction timestamps, and interval constraints.
- Documented and regression-tested package-root public API for `v0.1.0`.
- Python 3.11, 3.12, and 3.13 CI with lint, strict type checking, tests, and package builds.
- Clean-wheel installation smoke test that exercises the README normalization/validation path in a fresh environment.
- Public/private OSS extraction boundary, contribution guidance, security policy, and pull-request checklist.

### Deliberately deferred

- Checkpoint/recovery orchestration is deferred until a concrete public use case justifies a stable abstraction.
- Provider SDK adapters, production persistence, market calendars, trading signals, execution, and strategy logic remain outside the core.

## 0.1.0a0 - 2026-09-17

### Added

- Initial provider-independent package skeleton.
- Immutable source observations and deterministic fingerprints.
- Reference idempotent in-memory ingestion semantics.
- Canonical OHLCV bars and baseline validation.
- Point-in-time universe membership primitives.
- Historical-correction precondition verification.
- Public/private OSS extraction boundary, contribution guidance, and CI.
