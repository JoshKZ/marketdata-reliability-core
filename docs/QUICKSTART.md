# Offline CSV audit quick start

Requires Python 3.11+. The package has no third-party runtime dependencies and
performs no network requests. Installing/building from source may download build
tools; offline runtime does not mean offline first-time installation.
There is no PyPI publication in this release. Install from a reviewed checkout or
a verified wheel, not an assumed package-index entry with the same name.

## Install without activating a shell script

Clone this repository and change into it. For a stable baseline choose a published
release tag; `main` may contain changes that have not been tagged yet.

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install .
.venv\Scripts\python.exe -m marketdata_reliability --bars examples/data/bars_clean.csv --windows examples/data/windows.csv
$LASTEXITCODE
```

Linux/macOS (macOS is not currently in the CI matrix):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m marketdata_reliability --bars examples/data/bars_clean.csv --windows examples/data/windows.csv
echo $?
```

The clean synthetic example has five expected and covered slots, no findings,
and exit code 0. The installed `mdr-audit` command is equivalent to the module
entry point. In the commands below use your virtual environment's Python.

## See failures, not just a success demo

```bash
python -m marketdata_reliability --bars examples/data/bars_broken.csv --windows examples/data/windows.csv --output report.json
```

This intentionally exits **1**, with a completed JSON report: 5 expected slots,
5 input rows, 4 covered slots, 1 missing slot, 1 duplicate, coverage `"0.8"`, and
3 errors (missing, duplicate, invalid OHLC). The gap between the two sessions is
not an error. `report.json` must not already exist; choose a new filename for a
second run. The old Python examples remain available under `examples/`.

## CSV contract

Bars require exactly these columns (order can vary):

```csv
market,symbol,asset_class,start,end,open,high,low,close,volume
SYNTH,DEMO,equity,2026-01-02T09:00:00Z,2026-01-02T09:01:00Z,100,101,99,100.5,10
```

Windows require exactly these columns:

```csv
market,symbol,asset_class,start,end,interval_seconds
SYNTH,DEMO,equity,2026-01-02T09:00:00Z,2026-01-02T09:03:00Z,60
```

Use UTF-8, optionally with a BOM. LF and CRLF are supported. Header columns must
occur exactly once; unknown/missing columns, malformed records, NUL cells, and
blank records are rejected rather than silently ignored. Quoted CSV fields are
supported, but identifiers must not contain control characters or surrounding
whitespace. An empty bars file with a valid header means all declared slots are
missing. A completely empty file or empty window scope is an input error.

Timestamps must use `YYYY-MM-DDTHH:MM:SS[.ffffff]Z` or an explicit `+HH:MM` / `-HH:MM`
offset. Fractions contain 1-6 digits. Naive timestamps, inferred local timezones,
`-00:00` (unknown offset), and invalid dates are rejected. Resolve daylight-saving
ambiguities upstream. Windows are half-open and use positive whole-second
intervals. The Python API still accepts finer timedelta intervals.

Numeric cells use exact Decimal construction, not binary floats. A malformed
number aborts parsing. NaN/Infinity tokens are intentionally retained as bad Bar
values so the audit can report them as **data-quality findings**, with exit 1 by
default. This differs from `normalize_bar`, which rejects non-finite inputs.
No invalid price, negative volume, duplicate, or missing bar is automatically fixed.

Use one comparable dense series per audit. Supply separate windows for legal
breaks, holidays, halts, and no-trade-bar policy. The CLI does not infer calendars,
provider field names, adjusted-price conventions, or the historical universe.

## Exit codes and automation

| Exit | Meaning | JSON report |
| --- | --- | --- |
| 0 | Audit completed with no rejected findings under the selected policy. | Yes. |
| 1 | Audit completed with errors (or warnings when requested). | Yes. |
| 2 | Input/configuration/output error; audit delivery did not complete. | Do not consume an output as a new successful report. |

Help and version requests exit 0 without an audit report. On a normal audit,
stdout is JSON only and diagnostic errors go to stderr. Always check the exit
code; do not turn every nonzero exit into success with a blanket shell fallback.

`--warn CODE` explicitly downgrades a finding to WARNING and can be repeated.
`--warnings-as-errors` makes warnings cause exit 1 without changing the report's
severities, coverage, or `valid` property. A warning-only report is `valid` even
when data is missing. Check coverage/missing counts separately when completeness
is required. `python -m marketdata_reliability --help` lists available options;
code values are documented in [JSON_REPORT.md](JSON_REPORT.md).

`--output` exclusively creates a new UTF-8 file only after parsing, auditing, and
serialization succeed. Existing files, including input files and existing links,
are never overwritten by this option. Shell redirection (`>`) is controlled by
your shell and does not provide this protection. Output is not a durable atomic
transaction: an OS write failure may leave an incomplete newly created file.
Exit 2 means it must not be consumed as a completed report.

## Bounded batch processing

Defaults are `--max-file-bytes 16777216` (16 MiB per file), `--max-rows 100000`
(per file), and `--max-expected-bars 100000`. Override with explicit positive
integers or split the audit by day/instrument. Cells are limited to 4096 characters
and numeric cells to 128. The existing Python audit default remains 1,000,000
expected slots; the CLI uses a smaller initial batch bound.

No truncation or partial success is returned when a limit is exceeded. Input text
and results are held in memory; these limits are not a hard process-memory quota.
Use only trusted local file paths. The CLI is not a server, hostile-filesystem
sandbox, provider adapter, or streaming engine. Review report identifiers and
messages before sharing, even though raw price columns are not included.
