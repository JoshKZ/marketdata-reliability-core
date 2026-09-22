"""Verify the actual wheel built from sdist in a clean, cross-platform environment."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tarfile
import tempfile
import tomllib
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", timeout=120, check=False)
    if result.returncode != expected:
        raise RuntimeError(f"expected exit {expected}, got {result.returncode}\n"
                           f"{result.stdout}\n{result.stderr}")
    return result


def main() -> None:
    wheels = list((ROOT / "dist").glob("*.whl"))
    sources = list((ROOT / "dist").glob("*.tar.gz"))
    assert len(wheels) == len(sources) == 1
    expected_version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    with tarfile.open(sources[0]) as archive:
        names = archive.getnames()
        for required in ("docs/QUICKSTART.md", "docs/JSON_REPORT.md", "examples/data/bars_clean.csv",
                         "examples/data/bars_broken.csv", "examples/data/windows.csv",
                         "tests/test_cli.py", "scripts/smoke_distribution.py"):
            assert any(name.endswith("/" + required) for name in names), required
    with tempfile.TemporaryDirectory(prefix="mdrc-smoke-") as directory:
        isolated = Path(directory)
        environment = isolated / "venv"
        venv.create(environment, with_pip=True)
        bin_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        python = str(bin_dir / ("python.exe" if os.name == "nt" else "python"))
        command = str(bin_dir / ("mdr-audit.exe" if os.name == "nt" else "mdr-audit"))
        run([python, "-m", "pip", "install", "--no-index", "--no-deps", str(wheels[0])], isolated)
        code = '''
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
import marketdata_reliability as m
assert version("marketdata-reliability-core") == EXPECTED
assert files(m).joinpath("py.typed").is_file()
assert "site-packages" in Path(m.__file__).parts
start = datetime(2026, 1, 2, 9, tzinfo=UTC)
i = m.InstrumentId("SYNTH", "DEMO", "equity")
bar = m.normalize_bar({"open":"100", "high":"101", "low":"99", "close":"100", "volume":10},
                      instrument=i, start=start, end=start+timedelta(minutes=1))
assert m.validate_bars([bar], expected_interval=timedelta(minutes=1)) == []
report = m.audit_bars([bar], windows=[m.ValidationWindow(i, start, bar.end, timedelta(minutes=1))])
assert m.report_to_dict(report)["summary"]["valid"]
'''.replace("EXPECTED", repr(expected_version))
        run([python, "-I", "-c", code], isolated)
        for example in ("audit_two_sessions.py", "validate_broken_bars.py"):
            run([python, "-I", str(ROOT / "examples" / example)], isolated)
        for prefix in ([python, "-I", "-m", "marketdata_reliability"], [command]):
            assert expected_version in run(prefix + ["--version"], isolated).stdout
            run(prefix + ["--help"], isolated)
            args = ["--windows", str(ROOT / "examples/data/windows.csv"), "--bars"]
            clean_args = prefix + args + [str(ROOT / "examples/data/bars_clean.csv")]
            clean = run(clean_args, isolated)
            assert clean.stderr == ""
            summary = json.loads(clean.stdout)["summary"]
            assert summary["valid"] and summary["covered_bars"] == summary["expected_bars"] == 5
            assert run(clean_args, isolated).stdout == clean.stdout
            broken = run(prefix + args + [str(ROOT / "examples/data/bars_broken.csv")], isolated, 1)
            summary = json.loads(broken.stdout)["summary"]
            assert summary["observed_bars"] == 5 and summary["covered_bars"] == 4
            assert summary["missing_bars"] == summary["duplicate_bars"] == 1
            assert summary["coverage_ratio"] == "0.8" and summary["error_count"] == 3
            assert summary["count_by_code"] == {
                "missing_interval": 1, "duplicate_bar": 1, "invalid_ohlc": 1,
            }
            (ROOT / "dist/audit-example.json").write_text(broken.stdout, encoding="utf-8")
            absent = run(prefix + ["--bars", str(isolated / "absent.csv"), "--windows",
                                   str(ROOT / "examples/data/windows.csv")], isolated, 2)
            assert absent.stdout == "" and "Traceback" not in absent.stderr
    lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
             for path in sorted(wheels + sources)]
    (ROOT / "dist/SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Clean distribution smoke passed: package API, both CLI entry points, exit 0/1/2, examples.")


if __name__ == "__main__":
    main()
