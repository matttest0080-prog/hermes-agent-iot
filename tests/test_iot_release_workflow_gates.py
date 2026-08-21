from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SITE = ROOT / ".github" / "workflows" / "deploy-site.yml"


def test_vercel_release_deploy_is_gated_to_upstream_repository() -> None:
    jobs = yaml.safe_load(DEPLOY_SITE.read_text(encoding="utf-8"))["jobs"]
    condition = str(jobs["deploy-vercel"]["if"])
    assert "github.repository == 'NousResearch/hermes-agent'" in condition
