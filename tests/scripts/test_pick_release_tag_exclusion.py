"""A release candidate and its same-commit aliases cannot be OLD baselines."""
import json
import subprocess

import pytest

from tests.scripts.test_pick_release_tags import SCRIPT, _git, _origin_with_tags, _pick


@pytest.mark.parametrize("remote", [True, False])
def test_exclusion_removes_candidate_commit_and_aliases(tmp_path, remote):
    old, candidate = "iot-v0.22.2.post1", "iot-v0.22.5.post2"
    origin = _origin_with_tags(tmp_path, [old, candidate])
    seed = tmp_path / "seed"
    _git(seed, "tag", "v0.22.5")
    _git(seed, "push", str(origin), "refs/tags/v0.22.5")
    repo = tmp_path / "consumer"
    args = ["clone", "--no-local"] + (["--no-tags"] if remote else [])
    _git(tmp_path, *args, str(origin), str(repo))
    if not remote:
        _git(repo, "remote", "remove", "origin")
    selected = json.loads(_pick(repo, "--count", "5", "--exclude-ref", candidate))
    assert selected == [old]
    assert _git(repo, "for-each-ref", "refs/hermes-release-picker").stdout == ""


def test_excluding_only_available_commit_fails_instead_of_reporting_no_tests(tmp_path):
    candidate = "iot-v0.22.5.post2"
    origin = _origin_with_tags(tmp_path, [candidate])
    repo = tmp_path / "consumer"
    _git(tmp_path, "clone", "--no-local", "--no-tags", str(origin), str(repo))
    result = subprocess.run(["bash", str(SCRIPT), "--repo", str(repo), "--exclude-ref", candidate],
                            capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert "no reachable supported release tags" in result.stderr
