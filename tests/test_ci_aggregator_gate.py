"""The CI aggregator gate must fail closed.

``All required checks pass`` (job ``all-checks-pass`` in
``.github/workflows/ci.yml``) is the only check branch protection requires, so
the way it classifies ``needs`` results decides whether a pull request may
merge. A cancelled job -- an in-flight run superseded by a newer push -- or a
timed-out job produced no result at all; classifying those as "not a failure"
let a PR merge with the Python suite never having run.

These tests execute the workflow's own snippet rather than a copy of it, so a
future edit that reopens the hole fails here.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import textwrap

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
STEP_NAME = "name: Evaluate job results"


def _extract_evaluate_run_block() -> str:
    """Return the shell body of the 'Evaluate job results' step, dedented."""
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    assert STEP_NAME in text, f"{CI_WORKFLOW} no longer has a step named {STEP_NAME!r}"
    lines = text[text.index(STEP_NAME) :].splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "run: |":
            continue
        block_indent = len(line) - len(line.lstrip())
        body: list[str] = []
        for following in lines[index + 1 :]:
            if not following.strip():
                body.append("")
                continue
            if len(following) - len(following.lstrip()) <= block_indent:
                break
            body.append(following)
        return textwrap.dedent("\n".join(body)).strip("\n")
    raise AssertionError(f"'run: |' block not found under {STEP_NAME!r}")


def _run_gate(results: dict[str, str], tmp_path: pathlib.Path) -> subprocess.CompletedProcess:
    github_output = tmp_path / "github_output.txt"
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "NEEDS": json.dumps({name: {"result": r} for name, r in results.items()}),
        "GITHUB_OUTPUT": str(github_output),
    }
    return subprocess.run(
        ["bash", "-c", _extract_evaluate_run_block()],
        env=env,
        capture_output=True,
        text=True,
    )


def test_every_job_successful_passes(tmp_path):
    proc = _run_gate({"tests": "success", "lint": "success"}, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "All checks passed" in proc.stdout


def test_skipped_jobs_stay_benign(tmp_path):
    """Opt-in lanes express 'not run' as skipped; that must not fail the gate."""
    proc = _run_gate({"tests": "success", "e2e": "skipped"}, tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_a_failed_job_fails_the_gate(tmp_path):
    proc = _run_gate({"tests": "success", "lint": "failure"}, tmp_path)
    assert proc.returncode == 1
    assert "lint" in proc.stdout


def test_a_cancelled_job_fails_the_gate(tmp_path):
    """Regression: a run superseded by a newer push used to read as green."""
    proc = _run_gate({"tests": "cancelled", "lint": "success"}, tmp_path)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "tests" in proc.stdout


def test_a_timed_out_job_fails_the_gate(tmp_path):
    proc = _run_gate({"tests": "timed_out"}, tmp_path)
    assert proc.returncode == 1, proc.stdout + proc.stderr


def test_any_unexpected_result_state_fails_the_gate(tmp_path):
    """Unknown states must be treated as failing, not silently ignored."""
    for state in ("neutral", "action_required", "stale"):
        proc = _run_gate({"tests": state}, tmp_path)
        assert proc.returncode == 1, f"{state} was treated as green"


def test_needs_json_output_is_written_for_the_comment_assembler(tmp_path):
    proc = _run_gate({"tests": "failure", "lint": "skipped"}, tmp_path)
    written = (tmp_path / "github_output.txt").read_text(encoding="utf-8")
    match = re.search(r"^needs-json=(.+)$", written, re.MULTILINE)
    assert match, written
    assert json.loads(match.group(1)) == {"tests": "failure", "lint": "skipped"}
