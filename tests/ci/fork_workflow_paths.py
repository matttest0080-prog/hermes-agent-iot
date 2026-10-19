"""The IoT fork ships ``.github/workflows/ci.yml``, not upstream's ``ci.yaml``.

Upstream's CI routing suites (``test_update_ci_routing.py``,
``test_update_transitive_routing.py``, ``test_classify_changes.py``,
``test_live_comment.py``, ``test_stable_release_graph.py``) describe the lane
contract of ``ci.yaml``. A ``pull_request`` run only starts a workflow whose path
already exists on the base branch, so the fork keeps ``ci.yml`` until that rename
can land there — guarded by
``tests/test_iot_release_workflow_gates.py::test_iot_pr_ci_preserves_the_default_branch_workflow_path``.
Every reader of ``ci.yaml`` calls :func:`require_upstream_ci_yaml` instead of
crashing on a missing file, so the fork's divergence is one explicit skip rather
than 94 opaque failures.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_CI = ROOT / ".github" / "workflows" / "ci.yaml"
FORK_CI = ROOT / ".github" / "workflows" / "ci.yml"

SKIP_REASON = (
    "the IoT fork keeps .github/workflows/ci.yml: upstream's ci.yaml lane contract "
    "does not describe this repository"
)


def require_upstream_ci_yaml(path: str | Path) -> None:
    """Skip the calling test when *path* is ``ci.yaml`` and this checkout lacks it."""
    if Path(path) == UPSTREAM_CI and not UPSTREAM_CI.is_file():
        pytest.skip(SKIP_REASON)
