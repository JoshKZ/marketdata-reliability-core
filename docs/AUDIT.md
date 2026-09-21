# Session-aware dataset audit

`audit_bars` checks a dataset against **caller-declared expected bar windows**.
It does not download quotes, discover listings, infer trading hours, or fix prices.
Use it when you can declare exactly which start-labelled bars should exist.

## Declare the grid, not the exchange

```python
from datetime import UTC, datetime, timedelta
from marketdata_reliability import InstrumentId, ValidationWindow, audit_bars

instrument = InstrumentId("SYNTH", "DEMO", "equity")
start = datetime(2026, 1, 2, 9, tzinfo=UTC)
window = ValidationWindow(instrument, start, start + timedelta(minutes=3),
                          timedelta(minutes=1))
report = audit_bars([], windows=[window])
assert report.expected_bars == report.missing_bars == 3
assert not report.valid
```

Each window is half-open `[start, end)`. A three-minute window expects bars
`[09:00,09:01)`, `[09:01,09:02)`, and `[09:02,09:03)`, not a fourth bar at 09:03.
Windows must be non-empty, timezone-aware, and exactly divisible by a positive
interval. Same-instrument windows may touch but may not overlap or duplicate.
Different instruments may have overlapping windows; disjoint windows may use
different intervals. At least one window is required: an empty scope is not a
successful audit. A populated scope with zero observations reports every slot missing.

Split morning/afternoon, overnight breaks, and non-trading days into separate
windows. The core never searches for missing bars between these windows. A bar
whose start falls in an undeclared break is nevertheless reported as outside scope.
The caller owns holidays, early closes, halts, and whether a no-trade interval
should generate a bar at all. Sparse event-driven feeds need appropriately
selected windows; this release is **not** a calendar engine or halt detector.
Use one comparable dataset/price basis per audit; the core does not infer whether
prices are raw, adjusted, or comparable across sources.

## What the counts mean

| Attribute | Meaning |
| --- | --- |
| `expected_bars` | Sum of declared full grid slots. |
| `observed_bars` | Every input row, including duplicates, invalid and outside-scope rows. |
| `covered_bars` | Unique slots having an exact matching instrument/start/end. |
| `missing_bars` | `expected_bars - covered_bars`, including leading and trailing holes. |
| `duplicate_bars` | Extra rows sharing instrument/start/end, not the number of duplicated slots. |
| `outside_window_bars` | Rows whose start is not in a window for that instrument. |
| `coverage_ratio` | Covered / expected, using 28-digit Decimal precision. |
| `valid` | No ERROR issue remains under the selected severity policy. |

**Presence is not validity.** An exactly located bar with an impossible high or a
NaN still covers its slot and emits a data-quality error. A complete dataset can
therefore have `coverage_ratio == 1` and `valid == False`. Duplicates never push
coverage above 1. Wrong-duration, cross-boundary, and off-grid rows do not fill
expected slots. A row starting inside a window belongs to that window's observed
count even if its end is wrong; it is reported as misaligned, not silently clipped.

`report.windows` preserves caller window order. `report.by_instrument` provides
immutable instrument summaries, including unexpected instruments. Such an
instrument has zero expected bars and `coverage_ratio is None`, not 100%.
Dataset coverage is weighted by expected slot count, not an average of percentages.
`report.missing_timestamps` maps each instrument to a sorted tuple of missing UTC
**start** timestamps. Per-window missing timestamps are also available.

## Issues and severity

`issues` is an immutable tuple; `issue_count`, `error_count`, `warning_count`, and
read-only `count_by_code` are available at dataset, instrument, and window level.
Each issue can carry the original input `index`, declared `window_index`,
`instrument`, and UTC `timestamp`. Missing-slot issues have no input index.
One bad row can emit multiple issues; issue count is not bad-row count.

All findings default to ERROR. The audit accepts an explicit
`severity_overrides` mapping from `ValidationCode` to `ValidationSeverity`:

```python
from marketdata_reliability import ValidationCode, ValidationSeverity
report = audit_bars([], windows=[window], severity_overrides={
    ValidationCode.MISSING_INTERVAL: ValidationSeverity.WARNING,
})
assert report.valid and report.missing_bars == 3  # Caller intentionally accepted warnings.
```

Overrides change severity only, never coverage or finding counts. A warning-only
report is `valid`; applications needing completeness must also check `missing_bars`
or a coverage threshold. Policy mappings are copied, not modified. No persistent
global policy is installed. Legacy `validate_bar` / `validate_bars` keep their
list-returning APIs and do not inherit audit overrides.

Duplicates with different finite canonical OHLCV also emit `CONFLICTING_DUPLICATE`;
no preferred row is chosen. Non-finite or non-Decimal values passed directly to
`Bar` are reported before numeric comparisons. `normalize_bar` still performs
strict conversion and rejects non-finite values and binary floats. No price,
volume, or timestamp is automatically repaired.

## Time, ordering, and resource limits

All audit comparisons and grid arithmetic use UTC elapsed time. This avoids
collapsing distinct daylight-saving `fold` instants or inventing spring-forward
holes. Input objects are not mutated. Callers must still resolve ambiguous or
nonexistent local timestamps before passing them in; this library does not infer
the correct timezone or choose a fold. Non-Bar items and invalid window/policy
configuration raise exceptions instead of producing a partial success report.

Bar and window iterables may be generators. Input is not sorted in place.
Rows are processed once; missing slots are then emitted in declared-window order,
chronologically within each window. Results contain no current-clock timestamps.

`max_expected_bars=1_000_000` limits total expected-grid expansion **before reading
bars**. A larger declared scope raises a clear ValueError; split by instrument/day
or explicitly increase the positive integer limit. Nothing is silently truncated.
This limit bounds expected-slot expansion, not the number of supplied observations;
large inputs and large issue lists still require memory. Approximate work is
`O(B log W + E + W log W)` for B input rows, W windows, and E expected slots.

Run the complete offline example:

```bash
python examples/audit_two_sessions.py
```

Expected summary: 10 expected slots, 9 input rows, 8 covered slots, 2 missing,
1 duplicate, coverage 0.8, and 4 errors (including one invalid high).
