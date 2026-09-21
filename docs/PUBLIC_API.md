# Public API contract

The supported import surface is the package root, `marketdata_reliability`.
Internal helpers are not part of the compatibility contract.

## Retained 0.1.0 exports

| Area | Names |
| --- | --- |
| Canonical records | `InstrumentId`, `SourceObservation`, `build_observation`, `Bar` |
| Ingestion | `InMemoryObservationStore`, `InsertDisposition`, `ObservationCollisionError` |
| Normalization | `BarFieldMap`, `NormalizationError`, `normalize_bar` |
| Validation | `ValidationCode`, `ValidationIssue`, `validate_bar`, `validate_bars` |
| Historical membership | `UniverseInterval`, `members_at` |
| Provenance | `LineageRecord`, `build_lineage` |
| Correction checks | `CorrectionPreconditionFailed`, `CorrectionProposal`, `CorrectionReceipt`, `verify_correction` |

## Added in 0.2.0

- `ValidationWindow(instrument, start, end, expected_interval)` declares a dense,
  half-open expected grid. Boundaries are stored in UTC.
- `audit_bars(bars, *, windows, severity_overrides=None, max_expected_bars=1_000_000)`
  returns a `ValidationReport` without modifying inputs.
- `ValidationReport`, `WindowReport`, and `InstrumentReport` are frozen summary
  dataclasses with counts, immutable issues, and coverage/validity properties.
- `ValidationSeverity` defines `ERROR` and `WARNING`.

See [AUDIT.md](AUDIT.md) for full count, boundary, issue attribution, severity,
ordering, and resource semantics. Report objects are results, not authorization
certificates or evidence that a persistence operation occurred.

## Compatibility notes

All 22 original package-root names are retained. The new surface contains 28
names and is regression-tested. Existing `validate_bar()` and `validate_bars()`
call signatures and list-returning behavior remain. Legacy inter-row gap checks
are not silently made session-aware; use the explicit audit API instead.

`ValidationIssue` retains its first three constructor fields (`code`, `message`,
`index`) and appends optional `severity` (default ERROR), `instrument`,
`window_index`, and `timestamp`. Consumers that serialize dataclass fields should
account for these additional fields; the serialized field set is not unchanged.
Existing issue-code values remain; added codes are `NON_FINITE_VALUE`,
`INVALID_NUMERIC_TYPE`, `OUTSIDE_WINDOW`, `MISALIGNED_BAR`, and
`CONFLICTING_DUPLICATE`.

Directly constructed `Bar` values that violate the annotated Decimal contract
now produce validation findings before comparison instead of causing NaN-related
exceptions or silently accepting non-canonical types. Use `normalize_bar` for
numeric coercion. Source observation identity, lineage hashing, correction
preconditions, and historical membership implementations are unchanged.

Patch releases should preserve these public names and documented semantics.
Compatibility-sensitive changes require release notes and regression evidence.
No calendar, provider SDK, persistence layer, or trading interface is implied.
