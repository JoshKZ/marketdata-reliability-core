# Public API contract for v0.1.0

The package root is the supported import surface for the first stable release. Internal modules may change without compatibility guarantees unless an object is re-exported from `marketdata_reliability`.

## Supported names

### Canonical data and observations

- `InstrumentId`
- `SourceObservation`
- `build_observation`
- `Bar`

### Ingestion

- `InMemoryObservationStore`
- `InsertDisposition`
- `ObservationCollisionError`

### Normalization

- `BarFieldMap`
- `NormalizationError`
- `normalize_bar`

### Validation

- `ValidationCode`
- `ValidationIssue`
- `validate_bar`
- `validate_bars`

### Point-in-time membership

- `UniverseInterval`
- `members_at`

### Provenance

- `LineageRecord`
- `build_lineage`

### Historical correction preconditions

- `CorrectionPreconditionFailed`
- `CorrectionProposal`
- `CorrectionReceipt`
- `verify_correction`

## Compatibility policy

For `v0.1.x`, changes to these exported names or their core semantics should be treated as compatibility-sensitive and should include explicit release notes and regression tests. New provider adapters, persistence layers, trading logic, or proprietary integrations are not part of this public API contract.

The contract intentionally freezes a small reliability surface rather than promising stability for internal helpers or speculative extension points.
