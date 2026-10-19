"""Tests for scripts/pi2_benchmark.py (low-resource footprint measurement)."""
import json
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "pi2_benchmark.py"
FAST_CLI = [sys.executable, "-c", "pass"]


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )


def quick_args(out):
    return [
        "--quick",
        "--json",
        "--out",
        str(out),
        "--modules",
        "json",
        "--cli-cmd",
        " ".join(FAST_CLI),
    ]


def test_quick_run_emits_valid_json_with_measurements(tmp_path):
    out = tmp_path / "bench.json"
    proc = run(*quick_args(out))
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert set(data) >= {"label", "measured_at", "environment", "imports", "cli", "model"}
    assert data["environment"]["python"] == sys.version.split()[0]
    assert data["imports"][0]["module"] == "json"
    assert data["imports"][0]["peak_rss_kb"] > 0
    assert data["imports"][0]["import_s"] >= 0
    assert data["cli"][0]["exit_code"] == 0
    assert data["cli"][0]["wall_s"] >= 0
    assert json.loads(out.read_text(encoding="utf-8")) == data


def test_summary_mode_prints_human_readable_output(tmp_path):
    proc = run(
        "--quick",
        "--modules",
        "json",
        "--cli-cmd",
        " ".join(FAST_CLI),
        "--label",
        "unit-test",
    )
    assert proc.returncode == 0, proc.stderr
    assert "imports (fresh interpreter each):" in proc.stdout
    assert "cli:" in proc.stdout


def test_max_rss_gate_fails_when_the_budget_is_tiny(tmp_path):
    proc = run(*quick_args(tmp_path / "bench.json"), "--max-rss-kb", "1")
    assert proc.returncode == 1, proc.stdout
    assert "GATE" in proc.stderr


def test_compare_reports_deltas_against_a_previous_run(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    assert run(*quick_args(first)).returncode == 0
    proc = run(*quick_args(second), "--compare", str(first))
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["comparison"], "expected comparison rows"
    assert all({"metric", "was", "now", "delta"} <= set(row) for row in data["comparison"])


def test_missing_model_endpoint_is_reported_not_fatal(tmp_path):
    """A dead endpoint must not crash the benchmark (Pi2 has no model by default)."""
    proc = run(
        "--json",
        "--modules",
        "json",
        "--cli-cmd",
        " ".join(FAST_CLI),
        "--base-url",
        "http://127.0.0.1:1/v1",
        "--model",
        "nope",
        "--timeout",
        "2",
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["model"] and "error" in data["model"][0]
