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

    release_test_run = next(
        step["run"] for step in steps
        if step.get("name") == "Run release-focused tests"
    )
    assert "tests/test_publish_pypi_workflow.py" in release_test_run


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
