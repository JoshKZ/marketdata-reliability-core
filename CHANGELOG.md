# Changelog

All notable changes will be documented in this file.

## Unreleased

## 0.3.0 - 2026-09-22

### Added

- Offline `mdr-audit` and `python -m marketdata_reliability` commands for local bars/windows CSV.
- Versioned, detached JSON reporting with `report_to_dict` and `report_to_json`.
- Explicit exit codes for accepted audits, completed audits with rejected findings, and incomplete input/configuration/output handling.
- Strict UTF-8 CSV columns, explicit-offset timestamps, exact decimal parsing, bounded input, sanitized parser diagnostics, and no-overwrite output creation.
- Synthetic clean/broken CSV fixtures, Windows/Linux onboarding, JSON schema contract, maintenance evidence, and bug-report guidance.
- Windows Python 3.13 verification in addition to Linux Python 3.11-3.13.
- Source-distribution content checks and clean installed-wheel smoke tests for both CLI entry points and legacy APIs.
- Time-limited CI distribution artifacts with wheel, source archive, checksums, and a synthetic JSON report.

### Changed

- Preserve all 28 previous root exports and add two serializers; core validation, audit, observation identity, lineage, correction, and membership implementations remain unchanged.
- Use SPDX license metadata and setuptools >=77.0.3 for builds; retain zero third-party runtime dependencies.
- Pin CI actions to verified commit IDs, use read-only repository permissions, and disable persisted checkout credentials.
- Include documentation, examples, and tests in source distributions. Development extras include timezone data for Windows tests.

### Limits

- No PyPI publication, provider SDK, live data integration, trading features, private infrastructure, or independent security-audit claim.
- CLI is bounded batch processing, not streaming or a hostile-filesystem sandbox. Output writes are exclusive but not durable atomic transactions.
- Reports retain instrument identifiers and messages; inspect before sharing. Coverage still measures presence, not correctness.

## 0.2.0 - 2026-09-21

### Added

- Caller-declared, half-open ValidationWindow grids and session-aware audit_bars.
- Immutable dataset, instrument, and window summaries with weighted coverage and exact missing starts.
- Leading/trailing/empty-window detection without cross-session false gaps.
- Outside-window, grid-misalignment, and conflicting-duplicate diagnostics.
- Explicit ERROR/WARNING overrides that do not alter findings or coverage counts.
- UTC elapsed-time handling, DST regression tests, and an explicit expected-grid expansion limit.
- Synthetic two-session demo, audit contract, and clean-wheel audit smoke tests on Python 3.11-3.13.

### Fixed

- Direct Bar validation reports non-finite Decimal values and invalid numeric types instead of
  crashing during NaN comparison or accepting non-canonical numeric values.

### Compatibility

- All 22 original package-root names and legacy validation call signatures remain.
- ValidationIssue appends optional severity, instrument, window_index, and timestamp fields;
  dataclass serializers must account for them. Five additional validation codes are available.
- Legacy validate_bars remains calendar-unaware. Use audit_bars for scoped coverage.
- Observation IDs, lineage hashes, correction behavior, and membership logic are unchanged.

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
