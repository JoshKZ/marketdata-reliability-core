# Changelog

All notable changes will be documented in this file.

## Unreleased

### Added

- Explicit provider-field-to-canonical-bar normalization contract with safe decimal coercion.
- Deterministic multi-source lineage records for derived market-data records.
- Edge-case tests for timezone awareness, deterministic observation fingerprints, lineage identity, and normalization failures.
- Validation for bar durations that disagree with the declared expected interval.

### Changed

- Alpha package version advanced from `0.1.0a0` to `0.1.0a1` while the public API is hardened for `v0.1.0`.

## 0.1.0a0 - 2026-09-17

### Added

- Initial provider-independent package skeleton.
- Immutable source observations and deterministic fingerprints.
- Reference idempotent in-memory ingestion semantics.
- Canonical OHLCV bars and baseline validation.
- Point-in-time universe membership primitives.
- Historical-correction precondition verification.
- Public/private OSS extraction boundary, contribution guidance, and CI.
