"""PR-facing workflows must run on fork-available GitHub-hosted runners."""

from pathlib import Path

from ruamel.yaml import YAML

from tests.ci import _gha_expr as gha

ROOT = Path(__file__).resolve().parents[2]
_RUNNER_JOBS = (
    (".github/workflows/ci.yml", "detect"),
    (".github/workflows/docker.yml", "mode"),
    (".github/workflows/nix.yml", "pnpm-deps-hash"),
    (".github/workflows/lint.yml", "lint"),
    (".github/workflows/repo-guards.yml", "guards"),
    (".github/workflows/plugin-catalog-ci.yml", "structural"),
    (".github/workflows/label-rerun.yml", "rerun-with-e2e"),
    (".github/workflows/ci-review-comment.yml", "comment"),
)


def _runner(path: str, job: str) -> str:
    workflow = YAML(typ="safe").load((ROOT / path).read_text(encoding="utf-8"))
    return workflow["jobs"][job]["runs-on"]


def test_fork_pr_workflows_use_github_hosted_runner():
    context = {"github": {"repository_owner": "matttest0080-prog"}}
    for path, job in _RUNNER_JOBS:
        assert gha.render(_runner(path, job), context) == "ubuntu-24.04", (path, job)


def test_upstream_pr_workflows_keep_blacksmith_runner():
    context = {"github": {"repository_owner": "NousResearch"}}
    for path, job in _RUNNER_JOBS:
        assert gha.render(_runner(path, job), context) == "blacksmith-4vcpu-ubuntu-2404", (path, job)
