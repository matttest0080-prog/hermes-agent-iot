"""Stable runs on the default branch, so every lane must be told which commit to test."""
import re
from pathlib import Path

from ruamel.yaml import YAML

from tests.ci.fork_workflow_paths import require_upstream_ci_yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
LOCAL_CALL = re.compile(r"^\./\.github/workflows/(?P<name>[^/@]+)$")

# Reusable workflows that already named their commit input before this contract.
EXISTING_INPUT = {"pm-bundle.yml": "ref", "desktop-bundle-smoke.yml": "sha"}

# Checkouts that deliberately follow the controller (default-branch) tree, with the reason.
CONTROLLER_CHECKOUTS: dict[tuple[str, str], str] = {}


def load(name: str) -> dict:
    # The fork keeps ci.yml, not upstream's ci.yaml; skip this contract suite when the
    # reachable graph asks for ci.yaml rather than crash on the missing file.
    require_upstream_ci_yaml(WORKFLOWS / name)
    return YAML(typ="base").load((WORKFLOWS / name).read_text(encoding="utf-8"))


def local_calls(doc: dict):
    for job_name, job in (doc.get("jobs") or {}).items():
        match = LOCAL_CALL.match(job.get("uses", ""))
        if match:
            yield job_name, job, match["name"]


def reachable(root: str = "stable-release.yml") -> dict[str, dict]:
    seen: dict[str, dict] = {}
    pending = [root]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen[name] = load(name)
        pending.extend(called for _, _, called in local_calls(seen[name]))
    return seen


def commit_input(name: str) -> str:
    return EXISTING_INPUT.get(name, "commit")


def test_every_reusable_lane_accepts_a_commit():
    for name, doc in reachable().items():
        if name in {"stable-release.yml", "desktop-bundled-release.yml"}:
            continue  # The controller, and the workflow that admits the claim itself.
        inputs = (doc["on"]["workflow_call"] or {}).get("inputs") or {}
        assert commit_input(name) in inputs, f"{name} cannot be told which commit to test"


def test_every_call_forwards_the_commit():
    for name, doc in reachable().items():
        for job_name, job, called in local_calls(doc):
            if called == "desktop-bundled-release.yml":
                continue  # Admits the claim itself and checks out the admitted SHA.
            key = commit_input(called)
            assert key in (job.get("with") or {}), f"{name}:{job_name} does not pass {key} to {called}"
            if name not in {"stable-release.yml", "desktop-bundled-release.yml"}:
                # A nested call must pass its own commit down. An empty or hard-coded value
                # would silently test the controller tip.
                value = job["with"][key]
                assert "inputs.commit" in value, f"{name}:{job_name} passes {value!r} to {called}"


def test_every_checkout_follows_the_commit_input():
    for name, doc in reachable().items():
        if name in {"stable-release.yml", "desktop-bundled-release.yml"}:
            continue
        key = commit_input(name)
        for job_name, job in (doc.get("jobs") or {}).items():
            for index, step in enumerate(job.get("steps") or []):
                if not step.get("uses", "").startswith("actions/checkout"):
                    continue
                if (name, f"{job_name}[{index}]") in CONTROLLER_CHECKOUTS:
                    continue
                ref = (step.get("with") or {}).get("ref", "")
                assert f"inputs.{key}" in ref, f"{name}:{job_name}[{index}] checks out {ref or 'the default sha'}"


def test_stable_release_calls_pass_the_admitted_commit():
    jobs = load("stable-release.yml")["jobs"]
    for job_name, job, called in local_calls({"jobs": jobs}):
        if called == "desktop-bundled-release.yml":
            continue
        value = job["with"][commit_input(called)]
        assert value == "${{ needs.admit.outputs.commit }}", f"{job_name}: {value}"
        needs = job.get("needs", [])
        assert "admit" in ([needs] if isinstance(needs, str) else needs), f"{job_name} reads admit without needing it"


# Groups that name the run keep a stable run away from pushes to the same branch.
RUN_SCOPED = ("github.run_id", ("inputs.commit", "inputs.release"))
# docker.yml keys its group on the release phase, which a push never uses.
PHASE_SCOPED = {"docker.yml": "inputs.release-phase"}


def test_no_lane_shares_a_concurrency_group_with_pushes_to_the_default_branch():
    for name, doc in reachable().items():
        if name in {"stable-release.yml", "desktop-bundled-release.yml"}:
            continue
        blocks = [("workflow", doc.get("concurrency"))]
        blocks += [(job_name, job.get("concurrency")) for job_name, job in (doc.get("jobs") or {}).items()]
        for where, block in blocks:
            group = block.get("group", "") if isinstance(block, dict) else block or ""
            if not group:
                continue
            if name in PHASE_SCOPED:
                assert PHASE_SCOPED[name] in group, f"{name}:{where} group {group!r}"
                continue
            needed, scopes = RUN_SCOPED
            assert needed in group and any(scope in group for scope in scopes), \
                f"{name}:{where} group {group!r} would share main's group with a push"


# Uses of the triggering ref or SHA that are not a commit under test, with the reason each is safe.
CONTROLLER_REFERENCES = (
    ("github.event_name == 'push'", "a stable run is a workflow_dispatch, so push-only steps skip"),
    ("-${{ github.sha }}", "artifact display name, unique per run"),
    ("description:", "input documentation"),
    ("HEAD_REF:", "label on the lint summary"),
    ("key: visual-baselines-${{ github.ref_name }}", "restores main's baselines and never writes them for a stable run"),
    ("inputs.ref == github.sha", "saves candidates only for the triggering commit, so a stable claim never writes"),
    ("inputs.channel-build != '' && inputs.controller-sha", "smoke tests the staged artifact with the dispatched ref's scripts"),
    ("cancel-in-progress: ${{ inputs.release != true &&", "only decides whether a side-branch dispatch supersedes its predecessor; a stable run short-circuits on inputs.release"),
    # The install/update lane samples OLD baselines; its own tag must be excluded from that sample.
    # The value never selects the commit under test -- `test_exclude_ref_only_excludes_a_baseline`
    # pins that it reaches nothing but `--exclude-ref` and the self-baseline guard.
    ("EXCLUDE_REF: ${{ inputs.exclude-ref ||", "baseline exclusion only (see test_exclude_ref_only_excludes_a_baseline)"),
)
FALLBACK = re.compile(r"inputs\.(commit|ref|sha) \|\|")
REFERENCE = re.compile(r"GITHUB_SHA|github\.sha|github\.ref_name|github\.ref\b|GITHUB_REF")


def test_no_lane_uses_the_controller_commit_as_the_commit_under_test():
    for name in reachable():
        if name in {"stable-release.yml", "desktop-bundled-release.yml"}:
            continue
        for number, line in enumerate((WORKFLOWS / name).read_text(encoding="utf-8").splitlines(), 1):
            text = line.strip()
            if text.startswith(("#", "group:")) or not REFERENCE.search(text):
                continue
            if FALLBACK.search(text) or "inputs.commit" in text:
                continue
            assert any(allowed in text for allowed, _reason in CONTROLLER_REFERENCES), \
                f"{name}:{number} uses the triggering ref or SHA: {text}"


def test_exclude_ref_only_excludes_a_baseline():
    """`EXCLUDE_REF` may remove one OLD baseline tag from the sample, nothing else.

    The invariant above only knows "a lane must not use the triggering ref"; the install/update
    lane legitimately derives an exclusion from its own tag. This test pins the narrow shape of
    that exception: the value must never become the commit under test, a checkout ref, or the
    commit the lane claims to have tested.
    """
    name = "install-e2e.yml"
    lines = (WORKFLOWS / name).read_text(encoding="utf-8").splitlines()
    # Anchored shapes, not a generic "contains EXCLUDE_REF": the exception must stay narrow.
    allowed = (
        # the environment assignment that derives the exclusion
        re.compile(r'^EXCLUDE_REF: \$\{\{ inputs\.exclude-ref \|\|'),
        # refusing to sample the candidate as its own baseline
        re.compile(r'^\[ "\$INSTALL_REF" != "\$EXCLUDE_REF" \] \|\| '),
        # passing the value to the tag picker, and the optional pre-built argv
        re.compile(r'^tags="\$\(python3 -m scripts\.releases\.pick_tags .*--exclude-ref "\$EXCLUDE_REF"\)"$'),
        re.compile(r'^if \[ -n "\$EXCLUDE_REF" \]; then args\+=\(--exclude-ref "\$EXCLUDE_REF"\); fi$'),
    )
    forbidden = ("HERMES_TESTED_COMMIT", "ref:", "checkout", "INSTALL_REF=", "COMMIT_UNDER_TEST")

    usages = [(number, line.strip()) for number, line in enumerate(lines, 1) if "EXCLUDE_REF" in line]
    assert usages, f"{name}: EXCLUDE_REF disappeared; the baseline exclusion regressed"

    for number, text in usages:
        if text.startswith("#"):
            continue
        assert any(pattern.match(text) for pattern in allowed), (
            f"{name}:{number} unexpected EXCLUDE_REF use: {text}"
        )
        assert not any(token in text for token in forbidden), (
            f"{name}:{number} lets EXCLUDE_REF reach the commit under test: {text}"
        )
