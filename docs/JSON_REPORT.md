# JSON audit report contract: schema 1.0

`report_to_dict(report)` and `report_to_json(report, *, indent=2)` serialize a
completed `ValidationReport`. The CLI uses the same projection. This contract's
version is separate from package version 0.3.0. Internal dataclass field changes
are not automatically exposed in this format.

## Top-level fields

| Field | Type / meaning |
| --- | --- |
| `schema_version` | String `"1.0"`. |
| `report_type` | String `"marketdata-reliability/audit"`. |
| `coverage_basis` | String `"presence_not_validity"`. |
| `summary` | Aggregate count and policy-validity object. |
| `outside_window_bars` | Number of input rows starting outside declared scope. |
| `issues` | Findings once at dataset level, in audit issue order. |
| `windows` | Declared-order window objects, with exact missing UTC starts. |
| `instruments` | Instrument summaries, sorted by structured instrument identity. |

A summary contains integer `expected_bars`, `observed_bars`, `covered_bars`,
`missing_bars`, `duplicate_bars`, `issue_count`, `error_count`, and `warning_count`;
boolean `valid`; object `count_by_code`; and `coverage_ratio` as a **decimal string**
or JSON null for a zero denominator. Do not coerce this ratio to a binary float
when exact comparisons matter. Coverage never substitutes for checking errors.
A finding can be attached to multiple summaries, but appears only once in `issues`.

Every instrument is an object with `market`, `symbol`, and `asset_class`. It is
not encoded as a delimiter-joined mapping key. Instrument summaries also contain
`outside_window_bars` and the declared `window_indices` belonging to that instrument.

Windows contain `window_index`, `instrument`, UTC `start` and `end`, exact integer
`interval_microseconds`, `summary`, and `missing_timestamps`. Timestamp strings
use six fractional digits and `+00:00`. Windows keep the caller's declared order.
Missing timestamps are UTC bar starts, not row numbers.

Findings contain `code`, `severity` (`error`/`warning`), `message`, `index`,
`instrument`, `window_index`, and `timestamp`. Context can be null. `index` is the
zero-based original input row index; the CLI's parse errors instead identify
one-based data records. Multiline CSV records can occupy multiple physical lines.
Programs should inspect code/severity/counts rather than parse message prose.

Current code values: `invalid_interval`, `unexpected_duration`, `invalid_ohlc`,
`negative_volume`, `duplicate_bar`, `missing_interval`, `non_finite_value`,
`invalid_numeric_type`, `outside_window`, `misaligned_bar`, and `conflicting_duplicate`.
One row may have multiple findings. Warning policies never change missing counts.

## Determinism and safety

The projection is detached: mutating a returned dictionary cannot mutate the
original frozen report. JSON uses sorted object keys, ASCII escaping, and no NaN
numeric literals. `indent` accepts None or integers 0-8. The function does not
append a newline; the CLI does. Fixed reports serialize identically; changing
input row order can legitimately change original indices and issue order.

No current-clock timestamp, local file path, raw OHLCV values, source payload, or
credential field is added. This is **not** a redaction engine: existing instrument
names and caller-supplied issue messages may themselves be sensitive. JSON text
must still be treated as untrusted by downstream HTML/terminal renderers.

Serialization is not a signature, authenticity check, or revalidation of a report
constructed by a caller. It does not certify data truth or a completed database
correction. Incompatible field/type changes require a new schema major version;
consumers should tolerate documented additive fields and additional finding codes.
See [AUDIT.md](AUDIT.md) for the authoritative coverage and validity semantics.
