#!/usr/bin/env python3
"""Make the upstream release tag for this checkout available to Hermes version detection.

Fork checkouts do not automatically carry tags from NousResearch/hermes-agent. Hermes derives
its runtime version from release tags merged into HEAD, so a code sync can otherwise appear to
be the fork's older release in CI even though its matching upstream release commit is an ancestor.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

_UPSTREAM = "https://github.com/NousResearch/hermes-agent.git"
_VERSION_RE = re.compile(r"(?P<release>\d+\.\d+\.\d+)(?:\.post\d+)?\Z")


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=check, timeout=120,
    )


def _release_tag(repo: Path) -> str:
    try:
        metadata = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8-sig"))
        version = metadata["project"]["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot read project version from {repo / 'pyproject.toml'}: {exc}") from exc
    if not isinstance(version, str):
        raise ValueError("project.version must be a string")
    match = _VERSION_RE.fullmatch(version)
    if not match:
        raise ValueError(f"project.version {version!r} has no supported stable release tag")
    return f"v{match.group('release')}"


def fetch_release_tag(repo: Path, upstream: str) -> str:
    tag = _release_tag(repo)
    upstream_ref = f"refs/hermes-upstream-tags/{tag}"
    local_ref = f"refs/tags/{tag}"

    _git(repo, "update-ref", "-d", upstream_ref, check=False)
    try:
        _git(repo, "fetch", "--no-tags", upstream, f"refs/tags/{tag}:{upstream_ref}")
        upstream_commit = _git(repo, "rev-parse", f"{upstream_ref}^{{commit}}").stdout.strip()
        ancestor = _git(repo, "merge-base", "--is-ancestor", upstream_ref, "HEAD", check=False)
        if ancestor.returncode != 0:
            raise ValueError(f"upstream release tag {tag} is not an ancestor of HEAD")

        local = _git(repo, "show-ref", "--verify", "--quiet", local_ref, check=False)
        if local.returncode == 0:
            existing = _git(repo, "rev-parse", "--verify", "--quiet", f"{local_ref}^{{commit}}", check=False)
            if existing.returncode != 0 or existing.stdout.strip() != upstream_commit:
                raise ValueError(f"local {tag} conflicts with the upstream release tag")
        elif local.returncode == 1:
            _git(repo, "update-ref", local_ref, _git(repo, "rev-parse", upstream_ref).stdout.strip())
        else:
            raise subprocess.CalledProcessError(local.returncode, local.args, stderr=local.stderr)
        return tag
    finally:
        _git(repo, "update-ref", "-d", upstream_ref, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", default=_UPSTREAM, help="trusted upstream git repository")
    parser.add_argument(
        "--workspace", type=Path,
        default=Path(os.environ.get("GITHUB_WORKSPACE", Path(__file__).resolve().parents[2])),
    )
    args = parser.parse_args()
    try:
        tag = fetch_release_tag(args.workspace.resolve(), args.upstream)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"::error::Could not establish Hermes upstream release tag: {exc}", file=sys.stderr)
        return 1
    print(f"Hermes version identity: upstream release tag {tag} is reachable from HEAD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
