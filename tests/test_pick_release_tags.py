from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "sandbox" / "pick-release-tags.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "install-e2e.yml"


def test_release_picker_checkout_fetches_full_history() -> None:
    workflow = WORKFLOW.read_text()
    picker_job = workflow.split("  pick-releases:", 1)[1].split("\n  update:", 1)[0]

    assert "fetch-depth: 0" in picker_job


def test_release_workflow_triggers_for_iot_and_pi2_tags() -> None:
    workflow = WORKFLOW.read_text()
    assert "- 'iot-v*'" in workflow
    assert "- 'v[0-9]+.[0-9]+-pi2'" in workflow
    assert "- 'v[0-9]+.[0-9]+.[0-9]+-pi2'" in workflow


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return result.stdout.strip()


def test_picker_accepts_reachable_iot_and_pi2_release_tags(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=pi2-lite")
    _git(repo, "config", "user.name", "Release Test")
    _git(repo, "config", "user.email", "release-test@example.invalid")

    marker = repo / "marker"
    marker.write_text("first\n")
    _git(repo, "add", "marker")
    _git(repo, "commit", "-m", "first release")
    _git(repo, "tag", "iot-v0.20.0.post2")

    marker.write_text("second\n")
    _git(repo, "commit", "-am", "second release")
    _git(repo, "tag", "v1.2-pi2")

    marker.write_text("third\n")
    _git(repo, "commit", "-am", "third release")
    _git(repo, "tag", "v1.2.3-pi2")

    marker.write_text("fourth\n")
    _git(repo, "commit", "-am", "upstream calendar release")
    _git(repo, "tag", "v2026.8.3")

    # A tag on unrelated history must not become an update source for pi2-lite.
    _git(repo, "switch", "--orphan", "legacy")
    (repo / "legacy").write_text("legacy\n")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-m", "legacy release")
    _git(repo, "tag", "v11.1-pi2")
    _git(repo, "switch", "pi2-lite")

    result = subprocess.run(
        [str(SCRIPT), "--count", "5", "--repo", str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(result.stdout) == [
        "iot-v0.20.0.post2",
        "v1.2-pi2",
        "v1.2.3-pi2",
        "v2026.8.3",
    ]


def test_picker_treats_latest_created_cross_family_tag_as_newest(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=pi2-lite")
    _git(repo, "config", "user.name", "Release Test")
    _git(repo, "config", "user.email", "release-test@example.invalid")
    (repo / "marker").write_text("release\n")
    _git(repo, "add", "marker")
    _git(repo, "commit", "-m", "release history")
    _git(
        repo,
        "tag", "-a", "v2026.8.18", "-m", "older calendar release",
        env={"GIT_COMMITTER_DATE": "2026-08-18T00:00:00+00:00"},
    )
    _git(
        repo,
        "tag", "-a", "v11.2-pi2", "-m", "newer Pi2 release",
        env={"GIT_COMMITTER_DATE": "2026-08-20T00:00:00+00:00"},
    )

    result = subprocess.run(
        [str(SCRIPT), "--count", "1", "--repo", str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == ["v11.2-pi2"]
