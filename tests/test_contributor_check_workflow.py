import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "contributor-check.yml"
RESOLVER = ROOT / "scripts" / "contributor_merge_base.sh"


def _git(repo, *args, input_text=None):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def _history(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    tracked = repo / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD")
    tracked.write_text("head\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "head")
    return repo, base


def _resolve(repo, **values):
    env = os.environ.copy()
    env.update(
        PR_BASE_SHA="",
        PUSH_BEFORE_SHA="",
        DEFAULT_BRANCH="",
    )
    env.update(values)
    return subprocess.run(
        ["bash", str(RESOLVER)],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
    )


def test_workflow_delegates_merge_base_resolution_to_tested_helper():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "MERGE_BASE=$(bash scripts/contributor_merge_base.sh)" in source
    assert "origin/main" not in source


def test_resolver_uses_pull_request_base(tmp_path):
    repo, base = _history(tmp_path)
    result = _resolve(repo, PR_BASE_SHA=base, PUSH_BEFORE_SHA="malformed")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == base


def test_resolver_uses_push_before_sha(tmp_path):
    repo, base = _history(tmp_path)
    result = _resolve(repo, PUSH_BEFORE_SHA=base)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == base


def test_resolver_zero_push_sha_uses_verified_default_branch(tmp_path):
    repo, base = _history(tmp_path)
    _git(repo, "update-ref", "refs/remotes/origin/pi2-lite", base)
    result = _resolve(
        repo,
        PUSH_BEFORE_SHA="0" * 40,
        DEFAULT_BRANCH="pi2-lite",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == base


def test_resolver_rejects_malformed_push_sha(tmp_path):
    repo, _ = _history(tmp_path)
    result = _resolve(repo, PUSH_BEFORE_SHA="not-a-sha", DEFAULT_BRANCH="pi2-lite")
    assert result.returncode != 0
    assert "PUSH_BEFORE_SHA" in result.stderr


def test_resolver_rejects_missing_fallback_branch(tmp_path):
    repo, _ = _history(tmp_path)
    result = _resolve(repo)
    assert result.returncode != 0
    assert "DEFAULT_BRANCH" in result.stderr


def test_resolver_rejects_missing_default_branch_remote_ref(tmp_path):
    repo, _ = _history(tmp_path)
    result = _resolve(
        repo,
        PUSH_BEFORE_SHA="0" * 40,
        DEFAULT_BRANCH="pi2-lite",
    )
    assert result.returncode != 0
    assert "remote ref is unavailable" in result.stderr
    assert "refs/remotes/origin/pi2-lite" in result.stderr


def test_resolver_fails_closed_for_unrelated_pr_history(tmp_path):
    repo, _ = _history(tmp_path)
    tree = _git(repo, "mktree", input_text="")
    unrelated = _git(repo, "commit-tree", tree, "-m", "unrelated")
    result = _resolve(repo, PR_BASE_SHA=unrelated)
    assert result.returncode != 0
    assert "merge base" in result.stderr.lower()
