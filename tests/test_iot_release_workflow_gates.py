from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SITE = ROOT / ".github" / "workflows" / "deploy-site.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def test_iot_pr_ci_preserves_the_default_branch_workflow_path() -> None:
    """PR CI only fires when its workflow path also exists on the base branch."""
    assert CI_WORKFLOW.is_file()
    assert not CI_WORKFLOW.with_suffix(".yaml").exists()


def test_vercel_release_deploy_is_gated_to_upstream_repository() -> None:
    jobs = yaml.safe_load(DEPLOY_SITE.read_text(encoding="utf-8"))["jobs"]
    condition = str(jobs["deploy-vercel"]["if"])
    assert "github.repository == 'NousResearch/hermes-agent'" in condition
