#!/usr/bin/env python3
"""Prove ``blockExoticSubdeps`` still means what npm's ``allow-remote=root`` meant.

The fork replaced npm with pnpm, and npm's guarantee was that a *root* dependency may come from
a remote tarball (the fork's compat packages) while a *transitive* one may not — the line
``EALLOWREMOTE`` used to enforce. pnpm spells it ``blockExoticSubdeps``. This script pins both
halves with throwaway fixtures so the guard cannot be "equivalent" only on paper:

1. direct: a root dependency on a remote tarball must install;
2. nested: the same tarball forced onto a transitive dependency must fail with
   ``ERR_PNPM_EXOTIC_SUBDEP``.

Run where pnpm is available (CI's JS lane, or a Node 26 container):

    python3 scripts/ci/check_pnpm_exotic_subdeps.py --pnpm "npx --yes pnpm@12.15.0"

Exit codes: 0 both halves hold, 1 a half regressed, 2 the harness could not run.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

# The fork's own compat package: a real remote tarball, published only as a GitHub release asset.
REMOTE_TARBALL = (
    "https://github.com/matttest0080-prog/minimatch-hermes-compat/releases/download/"
    "v10.2.7-hermes.1/hermes-iot-minimatch-compat-10.2.7-hermes.1.tgz"
)


def _run(pnpm: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    # Keep pnpm's store and cache inside the fixture so runs cannot touch a user tree.
    env.setdefault("npm_config_store_dir", str(cwd / ".pnpm-store"))
    env.setdefault("XDG_CACHE_HOME", str(cwd / ".cache"))
    return subprocess.run(  # fixed argv, throwaway fixture
        [*pnpm, "install", "--ignore-scripts"],
        cwd=cwd, env=env, capture_output=True, text=True, timeout=900, check=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "exotic subdeps").splitlines()[0])
    parser.add_argument("--pnpm", default="pnpm", help="command that runs pnpm 12 (may include args)")
    args = parser.parse_args(argv)
    pnpm = shlex.split(args.pnpm)

    with tempfile.TemporaryDirectory(prefix="exotic-subdeps-") as tmp:
        base = Path(tmp)

        direct = base / "direct"
        direct.mkdir()
        (direct / "package.json").write_text(
            '{"name":"fx-direct","private":true,"version":"1.0.0","dependencies":'
            f'{{"minimatch":"{REMOTE_TARBALL}"}}}}\n',
            encoding="utf-8",
        )
        (direct / "pnpm-workspace.yaml").write_text("blockExoticSubdeps: true\n", encoding="utf-8")
        got = _run(pnpm, direct)
        if got.returncode != 0:
            print("FAIL direct: a root remote tarball must install under blockExoticSubdeps")
            print(got.stdout[-2000:])
            print(got.stderr[-2000:])
            return 1
        print("ok   direct: root remote tarball installed")

        nested = base / "nested"
        nested.mkdir()
        (nested / "package.json").write_text(
            '{"name":"fx-nested","private":true,"version":"1.0.0","dependencies":{"glob":"10.4.5"}}\n',
            encoding="utf-8",
        )
        (nested / "pnpm-workspace.yaml").write_text(
            "blockExoticSubdeps: true\n"
            "overrides:\n"
            f'  "minimatch@<11": "{REMOTE_TARBALL}"\n',
            encoding="utf-8",
        )
        got = _run(pnpm, nested)
        combined = got.stdout + got.stderr
        if got.returncode == 0:
            print("FAIL nested: a remote tarball on a transitive dependency was installed")
            return 1
        if "ERR_PNPM_EXOTIC_SUBDEP" not in combined:
            print("FAIL nested: refused, but not because of blockExoticSubdeps")
            print(combined[-2000:])
            return 1
        print("ok   nested: transitive remote tarball blocked (ERR_PNPM_EXOTIC_SUBDEP)")

    print("blockExoticSubdeps matches npm's allow-remote=root in both directions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
