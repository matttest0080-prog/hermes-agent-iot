import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-pypi.yml"
RELEASE_PYTHON = '"$RELEASE_PYTHON"'


def workflow_jobs():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return data["jobs"]


def test_build_job_uses_a_real_release_virtualenv_for_all_python_commands():
    build = workflow_jobs()["build"]
    assert build["env"]["RELEASE_PYTHON"] == ".release-venv/bin/python"

    steps = build["steps"]
    create_index = next(
        index for index, step in enumerate(steps)
        if step.get("name") == "Create isolated release virtual environment"
    )
    create_run = steps[create_index]["run"]
    assert "python -m venv .release-venv" in create_run

    guarded_steps = {
        "Install release test and build dependencies",
        "Run release-focused tests",
        "Validate tag, distribution name, and version",
        "Build and check artifacts",
    }
    found = set()
    for step in steps[create_index + 1:]:
        name = step.get("name")
        if name not in guarded_steps:
            continue
        found.add(name)
        run = step["run"]
        assert RELEASE_PYTHON in run, f"{name} bypasses the release virtualenv"
        assert "\npython " not in f"\n{run}", f"{name} invokes ambient python"

    assert found == guarded_steps

    install_run = next(
        step["run"] for step in steps
        if step.get("name") == "Install release test and build dependencies"
    )
    assert "uv==0.11.13" in install_run
    assert "uv sync --frozen --extra dev --extra rag" in install_run
    assert "pip install --disable-pip-version-check\n-e" not in install_run

    release_test_run = next(
        step["run"] for step in steps
        if step.get("name") == "Run release-focused tests"
    )
    assert "tests/test_publish_pypi_workflow.py" in release_test_run


def test_publish_jobs_are_gated_to_the_canonical_iot_repository():
    jobs = workflow_jobs()
    expected = "github.repository == 'matttest0080-prog/hermes-agent-iot'"
    assert str(jobs["build"]["if"]) == expected
    assert str(jobs["publish"]["if"]) == expected


def test_publish_job_only_downloads_and_publishes_the_tested_artifact():
    publish = workflow_jobs()["publish"]
    assert publish["needs"] == "build"
    assert publish["environment"] == "pypi"
    assert publish["permissions"] == {"id-token": "write"}
    uses = [step.get("uses", "") for step in publish["steps"]]
    assert not any(value.startswith("actions/checkout@") for value in uses)
    assert any(value.startswith("actions/download-artifact@") for value in uses)
    assert any(value.startswith("pypa/gh-action-pypi-publish@") for value in uses)
    assert not any("run" in step for step in publish["steps"])


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    ).stdout.strip()


def test_release_ancestry_gate_accepts_current_and_ancestor_but_rejects_off_branch(tmp_path):
    script = ROOT / "scripts" / "check_release_ancestry.sh"
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "release@example.invalid")
    _git(repo, "config", "user.name", "Release Test")
    (repo / "tracked").write_text("base\n")
    _git(repo, "add", "tracked")
    _git(repo, "commit", "-qm", "base")
    ancestor = _git(repo, "rev-parse", "HEAD")
    (repo / "tracked").write_text("tip\n")
    _git(repo, "commit", "-qam", "tip")
    tip = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/pi2-lite", tip)

    for accepted in (ancestor, tip):
        result = subprocess.run(
            ["bash", str(script), accepted], cwd=repo, text=True, capture_output=True
        )
        assert result.returncode == 0, result.stderr

    _git(repo, "checkout", "-qb", "off-branch", ancestor)
    (repo / "other").write_text("off\n")
    _git(repo, "add", "other")
    _git(repo, "commit", "-qm", "off")
    off_branch = _git(repo, "rev-parse", "HEAD")
    rejected = subprocess.run(
        ["bash", str(script), off_branch], cwd=repo, text=True, capture_output=True
    )
    assert rejected.returncode != 0
    assert "not an ancestor" in rejected.stderr


def test_workflow_fetches_authoritative_pi2_lite_and_runs_ancestry_gate_before_build():
    steps = workflow_jobs()["build"]["steps"]
    gate_index = next(i for i, step in enumerate(steps) if step.get("name") == "Verify tag ancestry")
    gate = steps[gate_index]
    assert "git fetch --no-tags origin" in gate["run"]
    assert "refs/remotes/origin/pi2-lite" in gate["run"]
    assert "scripts/check_release_ancestry.sh" in gate["run"]
    build_index = next(i for i, step in enumerate(steps) if step.get("name") == "Build and check artifacts")
    assert gate_index < build_index
