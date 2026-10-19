#!/usr/bin/env python3
"""Guard the JS/TS dependency surface of this repository.

Two checks, both ratcheted against a reviewed baseline so they can be adopted
without a flag day:

1. ``--pinned``   every *external* dependency in every ``package.json`` must be
   an exact version. Internal references (``workspace:``/``file:``/``link:``)
   are fine; anything else (``^``, ``~``, ``>``, ``*``, ``latest``, ``npm:``,
   ``git+`` ...) must be listed in the baseline's ``pinned_exceptions``.
   Rationale (borrowed from earendil-works/pi's ``check:pinned-deps``): ranged
   specifiers let a lockfile refresh pull unreviewed code; exact pins make every
   dependency change a reviewable diff.

2. ``--lifecycle`` no lockfile may gain a package that runs install/build
   lifecycle scripts (``hasInstallScript``) unless it is in the baseline's
   ``lifecycle`` list. Rationale (pi's shrinkwrap lifecycle-script allowlist):
   an install script executes arbitrary code at ``npm ci`` time, so a new one
   must be reviewed deliberately rather than arriving with a dependency bump.

Usage::

    python scripts/check_js_supply_chain.py --repo .              # both checks
    python scripts/check_js_supply_chain.py --repo . --pinned
    python scripts/check_js_supply_chain.py --repo . --lifecycle
    python scripts/check_js_supply_chain.py --repo . --update     # rewrite baseline

Exit codes: 0 clean, 1 violation(s) found, 2 usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

SKIP_DIRS = {
    "node_modules", ".git", ".venv", "venv", "dist", "build", "out", "coverage",
    ".next", ".turbo", ".cache", "site-packages", "__pycache__",
}
INTERNAL_PREFIXES = ("workspace:", "file:", "link:", "./", "../")
DEP_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
BASELINE_NAME = "js-supply-chain-baseline.json"
EXACT_RE = re.compile(r"^\d+\.\d+\.\d+")


def baseline_path(repo: str) -> str:
    return os.path.join(repo, "scripts", BASELINE_NAME)


def load_baseline(repo: str) -> dict:
    path = baseline_path(repo)
    if not os.path.isfile(path):
        return {"pinned_exceptions": [], "lifecycle": []}
    with open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    data.setdefault("pinned_exceptions", [])
    data.setdefault("lifecycle", [])
    return data


def save_baseline(repo: str, data: dict) -> str:
    path = baseline_path(repo)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ordered = {
        "pinned_exceptions": sorted(set(data["pinned_exceptions"])),
        "lifecycle": sorted(set(data["lifecycle"])),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(ordered, fh, indent=2)
        fh.write("\n")
    return path


def walk_package_jsons(repo: str):
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if "package.json" in filenames:
            yield os.path.relpath(os.path.join(dirpath, "package.json"), repo)


def walk_lockfiles(repo: str):
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if "package-lock.json" in filenames:
            yield os.path.relpath(os.path.join(dirpath, "package-lock.json"), repo)


def check_pinned(repo: str, baseline: dict):
    """Return (violations, seen) where violations are 'path#section#name=spec'."""
    allowed = set(baseline["pinned_exceptions"])
    violations, seen = [], []
    for rel in sorted(walk_package_jsons(repo)):
        try:
            with open(os.path.join(repo, rel), encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"  ! cannot read {rel}: {exc}")
            continue
        for section in DEP_SECTIONS:
            for name, spec in (data.get(section) or {}).items():
                if not isinstance(spec, str):
                    continue
                if spec.startswith(INTERNAL_PREFIXES):
                    continue
                if EXACT_RE.match(spec):
                    continue
                key = f"{rel}#{section}#{name}"
                seen.append(key)  # baseline snapshot: every ranged specifier
                if key not in allowed:
                    violations.append(f"{key}={spec}")
    return violations, seen


def _pkg_name_from_lock_key(key: str) -> str:
    """'node_modules/vite/node_modules/fsevents' -> 'fsevents'."""
    if "node_modules/" in key:
        return key.rsplit("node_modules/", 1)[1]
    return key


def lock_lifecycle_entries(repo: str, rel: str):
    """Yield 'lockfile::name@version' for every package with an install script."""
    with open(os.path.join(repo, rel), encoding="utf-8-sig") as fh:
        data = json.load(fh)
    out = []
    packages = data.get("packages")
    if isinstance(packages, dict):
        for key, entry in packages.items():
            if not key or not isinstance(entry, dict):
                continue  # "" is the working tree itself, not a dependency
            if entry.get("hasInstallScript"):
                out.append(f"{rel}::{_pkg_name_from_lock_key(key)}@{entry.get('version', '?')}")
    else:
        def walk(tree, prefix=""):
            for name, entry in (tree or {}).items():
                if not isinstance(entry, dict):
                    continue
                if entry.get("hasInstallScript"):
                    out.append(f"{rel}::{name}@{entry.get('version', '?')}")
                walk(entry.get("dependencies"), prefix + name + "/")
        walk(data.get("dependencies"))
    return out


def check_lifecycle(repo: str, baseline: dict):
    """Baseline and comparison both key on `name@version`; the lockfile path is
    reporting detail only, so moving a dependency between lockfiles is not a
    new lifecycle script."""
    allowed = set(baseline["lifecycle"])
    violations, seen = [], []
    for rel in sorted(walk_lockfiles(repo)):
        try:
            entries = lock_lifecycle_entries(repo, rel)
        except (OSError, ValueError) as exc:
            print(f"  ! cannot read {rel}: {exc}")
            continue
        for item in entries:
            name_version = item.split("::", 1)[1]
            seen.append(name_version)
            if name_version not in allowed:
                violations.append(item)
    return violations, seen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="JS dependency-surface guard (pins + lifecycle scripts)")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--pinned", action="store_true", help="only run the exact-pin check")
    ap.add_argument("--lifecycle", action="store_true", help="only run the lifecycle-script check")
    ap.add_argument("--update", action="store_true", help="rewrite the baseline from the current tree")
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        print(f"not a directory: {repo}", file=sys.stderr)
        return 2

    run_pinned = args.pinned or not args.lifecycle
    run_lifecycle = args.lifecycle or not args.pinned
    baseline = load_baseline(repo)

    pin_viol, pin_seen = check_pinned(repo, baseline) if run_pinned else ([], [])
    life_viol, life_seen = check_lifecycle(repo, baseline) if run_lifecycle else ([], [])

    if args.update:
        if run_pinned:
            baseline["pinned_exceptions"] = pin_seen
        if run_lifecycle:
            baseline["lifecycle"] = life_seen
        path = save_baseline(repo, baseline)
        print(f"baseline written: {os.path.relpath(path, repo)}")
        print(f"  pinned_exceptions: {len(baseline['pinned_exceptions'])}")
        print(f"  lifecycle:         {len(baseline['lifecycle'])}")
        return 0

    failed = False
    if run_pinned:
        print(f"exact-pin check: {len(pin_seen)} external specifier(s) inspected, {len(pin_viol)} violation(s)")
        for v in pin_viol:
            print(f"  VIOLATION {v}")
            print("            pin it exactly (or add the key to the baseline's pinned_exceptions)")
        failed = failed or bool(pin_viol)
    if run_lifecycle:
        print(f"lifecycle-script check: {len(life_seen)} install-script package(s) seen, {len(life_viol)} new")
        for v in life_viol:
            print(f"  VIOLATION {v}")
            print("            review the script, then add it to the baseline's lifecycle list")
        failed = failed or bool(life_viol)

    if failed:
        print("\nJS supply-chain guard failed.")
        return 1
    print("\nJS supply-chain guard passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
