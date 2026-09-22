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

## Added in 0.3.0

- `report_to_dict(report: ValidationReport) -> dict[str, object]` returns a detached,
  JSON-compatible projection with schema version `1.0`.
- `report_to_json(report: ValidationReport, *, indent: int | None = 2) -> str` uses
  the same projection, sorted keys, ASCII escaping, and no non-finite JSON numbers.
  Indentation must be None or an integer between 0 and 8. No newline is appended.

All 28 previous names remain; the complete root surface now contains 30 names
and is regression-tested. The new serializers do not mutate, authenticate, or
revalidate the supplied report. See [JSON_REPORT.md](JSON_REPORT.md) for the wire
format; do not depend on `dataclasses.asdict` as a public serialization contract.

The new `mdr-audit` executable and `python -m marketdata_reliability` share the
[documented CLI contract](QUICKSTART.md), including exit codes and strict CSV
formats. CSV/parser helpers are private, not new supported Python imports.
The CLI's whole-second windows and smaller default limits do not change the
existing Python API's timedelta support or `max_expected_bars` default.

## Compatibility notes

All 22 original package-root names and existing `validate_bar()` / `validate_bars()`
call signatures and list-returning behavior remain. Legacy inter-row gap checks
are not silently made session-aware; use the explicit audit API instead.

In 0.2.0, `ValidationIssue` retained its first three constructor fields (`code`,
`message`, `index`) and appended optional `severity` (default ERROR), `instrument`,
`window_index`, and `timestamp`. Consumers that serialize dataclass fields should
account for these additional fields; the serialized field set is not unchanged.
Existing issue-code values remain; 0.2.0 added `NON_FINITE_VALUE`,
`INVALID_NUMERIC_TYPE`, `OUTSIDE_WINDOW`, `MISALIGNED_BAR`, and
`CONFLICTING_DUPLICATE`. No further issue codes are added in 0.3.0.

Directly constructed `Bar` values that violate the annotated Decimal contract
produce validation findings before comparison instead of causing NaN-related
exceptions or silently accepting non-canonical types. Use `normalize_bar` for
numeric coercion. The CSV CLI deliberately preserves parseable NaN/Infinity as
findings; `normalize_bar` continues to reject non-finite numeric inputs.

Source observation identity, lineage hashing, correction preconditions,
historical membership, and session-audit implementation are unchanged in 0.3.0.
Patch releases should preserve these public names and documented semantics.
Compatibility-sensitive changes require release notes and regression evidence.
No calendar, provider SDK, persistence layer, or trading interface is implied.
