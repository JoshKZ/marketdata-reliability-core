import csv
import io
import json
from pathlib import Path

import pytest

from marketdata_reliability.cli import main

BAR_HEADER = ["market", "symbol", "asset_class", "start", "end", "open", "high", "low", "close", "volume"]
WINDOW_HEADER = ["market", "symbol", "asset_class", "start", "end", "interval_seconds"]
ROW = ["SYNTH", "DEMO", "equity", "2026-01-02T09:00:00Z", "2026-01-02T09:01:00Z",
       "100", "101", "99", "100.5", "10"]
WINDOW = ROW[:5] + ["60"]


def write_csv(path, header, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(header)
    writer.writerows(rows)
    path.write_text(stream.getvalue(), encoding="utf-8", newline="")


def inputs(tmp_path, rows=None, windows=None):
    bars, scope = tmp_path / "bars.csv", tmp_path / "windows.csv"
    write_csv(bars, BAR_HEADER, [ROW] if rows is None else rows)
    write_csv(scope, WINDOW_HEADER, [WINDOW] if windows is None else windows)
    return ["--bars", str(bars), "--windows", str(scope)]


def test_clean_audit_stdout_is_only_json(tmp_path, capsys):
    assert main(inputs(tmp_path)) == 0
    out, err = capsys.readouterr()
    assert err == ""
    data = json.loads(out)
    assert data["summary"]["valid"] is True
    assert data["summary"]["coverage_ratio"] == "1"
    assert data["summary"]["observed_bars"] == 1
    assert data["issues"] == []


def test_empty_bars_are_a_completed_failed_audit(tmp_path, capsys):
    assert main(inputs(tmp_path, rows=[])) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["expected_bars"] == data["summary"]["missing_bars"] == 1
    assert data["issues"][0]["index"] is None


def test_duplicate_conflict_and_original_input_index(tmp_path, capsys):
    changed = ROW.copy()
    changed[8] = "100.75"
    assert main(inputs(tmp_path, rows=[ROW, changed])) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["covered_bars"] == 1
    assert data["summary"]["duplicate_bars"] == 1
    assert data["summary"]["count_by_code"]["conflicting_duplicate"] == 1
    assert all(issue["index"] == 1 for issue in data["issues"])


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("column", [5, 6, 7, 8, 9])
def test_nonfinite_prices_are_findings_not_crashes(tmp_path, capsys, value, column):
    row = ROW.copy()
    row[column] = value
    assert main(inputs(tmp_path, rows=[row])) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["coverage_ratio"] == "1"
    assert data["summary"]["count_by_code"]["non_finite_value"] == 1


@pytest.mark.parametrize("value", ["2026-01-02T09:00:00", "2026-01-02", "2026-02-30T09:00:00Z",
                                  "2026-01-02T09:00:00-00:00", "2026-01-02T09:00:00+01:99",
                                  "2026-01-02T09:00:00.1234567Z"])
def test_ambiguous_or_invalid_timestamps_fail_without_report(tmp_path, capsys, value):
    row = ROW.copy()
    row[3] = value
    assert main(inputs(tmp_path, rows=[row])) == 2
    out, err = capsys.readouterr()
    assert out == "" and "timestamp" in err


def test_timezone_offsets_match_declared_utc_window(tmp_path, capsys):
    row = ROW.copy()
    row[3:5] = ["2026-01-02T17:00:00+08:00", "2026-01-02T17:01:00+08:00"]
    assert main(inputs(tmp_path, rows=[row])) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["covered_bars"] == 1


def test_bom_and_crlf_are_accepted(tmp_path, capsys):
    args = inputs(tmp_path)
    for path in (Path(args[1]), Path(args[3])):
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["valid"]


@pytest.mark.parametrize("kind", ["duplicate-header", "extra-header", "short-row", "blank-row", "empty-file",
                                 "malformed-quote", "invalid-utf8", "oversized-cell", "nul-cell"])
def test_malformed_input_never_produces_a_success_report(tmp_path, capsys, kind):
    args = inputs(tmp_path)
    path = Path(args[1])
    if kind == "duplicate-header":
        write_csv(path, BAR_HEADER[:-1] + ["close"], [ROW])
    elif kind == "extra-header":
        write_csv(path, BAR_HEADER + ["extra"], [ROW + ["x"]])
    elif kind == "short-row":
        write_csv(path, BAR_HEADER, [ROW[:-1]])
    elif kind == "blank-row":
        path.write_bytes(path.read_bytes() + b"\r\n")
    elif kind == "empty-file":
        path.write_bytes(b"")
    elif kind == "malformed-quote":
        path.write_bytes(path.read_bytes() + b'"unclosed')
    elif kind == "invalid-utf8":
        path.write_bytes(b"\xff")
    else:
        row = ROW.copy()
        row[1] = "x" * 4097 if kind == "oversized-cell" else "x\x00y"
        write_csv(path, BAR_HEADER, [row])
    assert main(args) == 2
    out, err = capsys.readouterr()
    assert out == "" and err.startswith("mdr-audit:")


@pytest.mark.parametrize("option,value", [("--max-file-bytes", "10"), ("--max-rows", "1"),
                                        ("--max-expected-bars", "1")])
def test_limits_fail_without_partial_report(tmp_path, capsys, option, value):
    window = WINDOW.copy()
    window[4] = "2026-01-02T09:02:00Z"
    args = inputs(tmp_path, rows=[ROW, ROW], windows=[window])
    assert main(args + [option, value]) == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("windows", [[], [WINDOW, WINDOW], [WINDOW[:-1] + ["0"]],
                                    [WINDOW[:-1] + ["1.5"]]])
def test_bad_scope_is_not_an_accepted_empty_audit(tmp_path, capsys, windows):
    assert main(inputs(tmp_path, windows=windows)) == 2
    assert capsys.readouterr().out == ""


def test_policy_changes_exit_code_but_not_coverage(tmp_path, capsys):
    args = inputs(tmp_path, rows=[]) + ["--warn", "missing_interval"]
    assert main(args) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["missing_bars"] == 1 and data["summary"]["valid"]
    assert main(args + ["--warnings-as-errors"]) == 1
    strict = json.loads(capsys.readouterr().out)
    assert strict == data


def test_output_is_new_file_only_and_inputs_are_unchanged(tmp_path, capsys):
    args = inputs(tmp_path, rows=[])
    source = Path(args[1])
    before = source.read_bytes()
    assert main(args + ["--output", str(source)]) == 2
    assert source.read_bytes() == before
    capsys.readouterr()
    output = tmp_path / "report.json"
    assert main(args + ["--output", str(output)]) == 1
    assert capsys.readouterr().out == ""
    assert json.loads(output.read_text())["summary"]["missing_bars"] == 1
    report_before = output.read_bytes()
    assert main(args + ["--output", str(output)]) == 2
    assert output.read_bytes() == report_before


def test_late_parse_error_creates_no_output_and_does_not_echo_cell(tmp_path, capsys):
    bad = ROW.copy()
    bad[5] = "private-value-DO-NOT-LOG"
    args = inputs(tmp_path, rows=[ROW, bad])
    output = tmp_path / "report.json"
    assert main(args + ["--output", str(output)]) == 2
    out, err = capsys.readouterr()
    assert out == "" and not output.exists()
    assert "record 2" in err and "private-value" not in err


def test_invalid_decimal_is_rejected_even_with_disabled_caller_trap(tmp_path, capsys):
    from decimal import InvalidOperation, localcontext

    row = ROW.copy()
    row[8] = "not-a-decimal"
    with localcontext() as context:
        context.traps[InvalidOperation] = False
        assert main(inputs(tmp_path, rows=[row])) == 2
    assert capsys.readouterr().out == ""


def test_missing_file_and_directory_fail_without_traceback(tmp_path, capsys):
    args = inputs(tmp_path)
    Path(args[1]).unlink()
    assert main(args) == 2
    assert "Traceback" not in capsys.readouterr().err
    args[1] = str(tmp_path)
    assert main(args) == 2
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_help_and_version_do_not_require_inputs(capsys, flag):
    with pytest.raises(SystemExit) as exc:
        main([flag])
    assert exc.value.code == 0
    assert "mdr-audit" in capsys.readouterr().out


@pytest.mark.parametrize("args", [["--max-rows", "0"], ["--max-rows", "-1"],
                                 ["--warn", "typo"], ["--max-ro", "100"]])
def test_invalid_arguments_exit_two(tmp_path, args):
    with pytest.raises(SystemExit) as exc:
        main(inputs(tmp_path) + args)
    assert exc.value.code == 2


def test_unicode_identity_is_preserved_in_ascii_json(tmp_path, capsys):
    row, window = ROW.copy(), WINDOW.copy()
    row[1] = window[1] = "\u6e2c\u8a66"
    assert main(inputs(tmp_path, rows=[row], windows=[window])) == 0
    text = capsys.readouterr().out
    assert text.isascii()
    assert json.loads(text)["instruments"][0]["instrument"]["symbol"] == "\u6e2c\u8a66"
