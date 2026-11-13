#!/usr/bin/env python3
"""Vendor a resource-bound build of minimatch from an official release tarball.

Why this exists
---------------
``GHSA-g3hv-75wg-m249`` / ``CVE-2026-118764`` (minimatch globparts amplification) is fixed
in upstream 11.0.1 for every ``>=7.0.0`` release, but 9.x and 10.x are still affected and
upstream has not shipped a backport. pnpm's ``blockExoticSubdeps`` forbids resolving a
transitive dependency to a remote tarball, so the fork cannot keep pointing nested
``minimatch`` consumers at a GitHub release asset: it vendors the runtime instead and points
``overrides`` at the local directory with the ``link:`` protocol.

What it does
------------
Extracts the runtime JavaScript *and* the type declarations (the package's own ``exports`` map
names ``types`` paths, so dropping them would ship a broken type surface), applies the two
bounds upstream 11.0.1 added, and re-points ``main``/``module``/``types``/``exports`` at
``compat/`` so the callable CommonJS default and the ESM default+named exports match the
interface the fork's previous compat tarball exposed.

Both edits are asserted to apply verbatim; a base-version drift fails loudly instead of
producing a silently unpatched package. Extraction is member-by-member with a path check
(``tarfile.extractall`` is never used), and the output directory must be an
``vendor/minimatch-compat-<x.y.z>`` child of this repository.

Usage
-----
    npm pack minimatch@10.2.6 --pack-destination /tmp/mm
    python3 scripts/ci/build_vendored_minimatch.py --tarball /tmp/mm/minimatch-10.2.6.tgz \\
        --out vendor/minimatch-compat-10.2.6 --source-commit ded1bbd0
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_ROOT = REPO_ROOT / "vendor"
OUT_PATTERN = re.compile(r"minimatch-compat-\d+\.\d+\.\d+$")

# Applied to dist/{commonjs,esm}/index.js. Each tuple is (old, new) and must match exactly once
# per file; the upstream 11.0.1 construct is quoted above each edit.
HUNKS: tuple[tuple[str, str], ...] = (
    # 11.0.1: `const { braceExpandMax = 100_000 } = this.options` inside firstPhasePreProcess.
    (
        "    firstPhasePreProcess(globParts) {\n        let didSomething = false",
        "    firstPhasePreProcess(globParts) {\n"
        "        // Backport of upstream 11.0.1 (GHSA-g3hv-75wg-m249): bound `**` amplification.\n"
        "        const { braceExpandMax = 100_000 } = this.options\n"
        "        let didSomething = false",
    ),
    # 11.0.1: the guard also fires when the expansion budget is spent.
    (
        "                        p2 === '..') {\n                        continue",
        "                        p2 === '..' ||\n"
        "                        globParts.length >= braceExpandMax) {\n                        continue",
    ),
    # 11.0.1: optional de-duplication is skipped above 1000 parts (quadratic comparisons).
    (
        "    secondPhasePreProcess(globParts) {\n        for (let i = 0",
        "    secondPhasePreProcess(globParts) {\n"
        "        // Backport of upstream 11.0.1 (GHSA-g3hv-75wg-m249): skip quadratic de-duplication.\n"
        "        if (globParts.length > 1000)\n            return globParts\n"
        "        for (let i = 0",
    ),
)

# Runtime + declarations. Declarations are required: the package's exports map names them.
KEEP_SUFFIXES = (".js", ".d.ts", ".d.mts", ".d.cts")
KEEP_ROOT_FILES = ("LICENSE", "LICENSE.md", "README.md")

# The vendored copy is a workspace project, so npm sees a standalone package here and would
# resolve it from the registry - past pnpm-workspace.yaml's overrides and release-age gate. Every
# other workspace folder refuses npm the same way: an unsatisfiable `engines.npm` plus
# `engine-strict=true`, which turns any command that builds a dependency tree into a refusal.
# (tests-js/npm-refused-in-workspaces.test.mjs asserts this for every workspace folder.)
NPM_REFUSAL = "npm is refused here: run pnpm install --frozen-lockfile at the repository root"
NPMRC = """# npm treats this vendored package as a project of its own and would resolve it from the
# registry, past pnpm-workspace.yaml's overrides and release-age gate. engines.npm in
# package.json is no valid range, and engine-strict turns that into a refusal for every command
# that builds a dependency tree here (install, ci, update, dedupe, uninstall, link,
# --package-lock-only, --ignore-scripts, --force). pnpm ignores both. Generated file: edit
# scripts/ci/build_vendored_minimatch.py, not this copy.
engine-strict=true
"""
PACKAGE_FIELDS = ("license", "engines", "keywords", "author")

COMPAT_CJS = (
    "'use strict'\n"
    "const engine = require('../dist/commonjs/index.js')\n"
    "module.exports = Object.assign(engine.minimatch, engine)\n"
)
COMPAT_MJS = (
    "import * as engine from '../dist/esm/index.js'\n"
    "export * from '../dist/esm/index.js'\n"
    "export default engine.minimatch\n"
)
COMPAT_DTS = (
    "export * from '../dist/esm/index.js'\n"
    "export { minimatch as default } from '../dist/esm/index.js'\n"
    "export type IOptions = import('../dist/esm/index.js').MinimatchOptions\n"
    "export type IMinimatch = import('../dist/esm/index.js').Minimatch\n"
)
COMPAT_DCTS = (
    "import * as engine from '../dist/commonjs/index.js'\n"
    "declare function minimatch(path: string, pattern: string, options?: engine.MinimatchOptions): boolean\n"
    "declare namespace minimatch {\n"
    "  const minimatch: typeof engine.minimatch\n"
    "  const Minimatch: typeof engine.Minimatch\n"
    "  type Minimatch = engine.Minimatch\n"
    "  type IMinimatch = engine.Minimatch\n"
    "  type IOptions = engine.MinimatchOptions\n"
    "  type MinimatchOptions = engine.MinimatchOptions\n"
    "  type MMRegExp = engine.MMRegExp\n"
    "  type ParseReturn = engine.ParseReturn\n"
    "  type ParseReturnFiltered = engine.ParseReturnFiltered\n"
    "  type Platform = engine.Platform\n"
    "  type Sep = engine.Sep\n"
    "  const GLOBSTAR: typeof engine.GLOBSTAR\n"
    "  const sep: typeof engine.sep\n"
    "  const filter: typeof engine.filter\n"
    "  const defaults: typeof engine.defaults\n"
    "  const braceExpand: typeof engine.braceExpand\n"
    "  const makeRe: typeof engine.makeRe\n"
    "  const match: typeof engine.match\n"
    "  const AST: typeof engine.AST\n"
    "  const escape: typeof engine.escape\n"
    "  const unescape: typeof engine.unescape\n"
    "}\n"
    "export = minimatch\n"
)


def _safe_members(tar: tarfile.TarFile) -> list[tarfile.TarInfo]:
    """Only regular files under ``package/`` with a plain relative path."""
    kept: list[tarfile.TarInfo] = []
    for member in tar.getmembers():
        if not member.isfile():
            continue
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "package":
            raise SystemExit(f"refusing suspicious tarball member: {member.name}")
        kept.append(member)
    return kept


def _check_out_path(out: Path) -> Path:
    resolved = out.resolve()
    if resolved.parent != VENDOR_ROOT.resolve():
        raise SystemExit(f"--out must be a direct child of {VENDOR_ROOT}, got {resolved}")
    if not OUT_PATTERN.fullmatch(resolved.name):
        raise SystemExit(f"--out basename must look like minimatch-compat-<x.y.z>, got {resolved.name}")
    return resolved


def _apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig")
    for old, new in HUNKS:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"{path}: expected exactly one match for a backport hunk, found {count}")
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "vendor minimatch").splitlines()[0])
    parser.add_argument("--tarball", required=True, type=Path, help="official minimatch tarball")
    parser.add_argument("--out", required=True, type=Path, help="vendor/minimatch-compat-<version>")
    parser.add_argument("--source-commit", default="", help="upstream commit this release was cut from")
    args = parser.parse_args(argv)

    out = _check_out_path(args.out)

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "package"
        root.mkdir()
        with tarfile.open(args.tarball) as tar:
            for member in _safe_members(tar):
                rel = PurePosixPath(member.name).relative_to("package")
                target = root.joinpath(*rel.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                handle = tar.extractfile(member)
                if handle is None:
                    raise SystemExit(f"unreadable tarball member: {member.name}")
                with handle, target.open("wb") as dst:
                    shutil.copyfileobj(handle, dst)

        meta = json.loads((root / "package.json").read_text(encoding="utf-8-sig"))
        version = meta["version"]
        if version.endswith("-hermes.1"):
            raise SystemExit("refusing a pre-patched source; vendor from the official release")
        if out.name != f"minimatch-compat-{version}":
            raise SystemExit(f"{out.name} does not carry the source version {version}")

        if out.exists():
            shutil.rmtree(out)
        (out / "dist").mkdir(parents=True)

        copied: list[Path] = []
        for src in sorted((root / "dist").rglob("*")):
            if not src.is_file() or not src.name.endswith(KEEP_SUFFIXES):
                continue
            dest = out / "dist" / src.relative_to(root / "dist")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            copied.append(dest)
        for entry in ("commonjs", "esm"):
            for needed in ("index.js", "index.d.ts"):
                if not (out / "dist" / entry / needed).is_file():
                    raise SystemExit(f"missing {entry}/{needed}; unexpected tarball layout")

        for entry in ("commonjs", "esm"):
            _apply(out / "dist" / entry / "index.js")
        # Node infers a module's type from the nearest package.json. Without these the ESM build is
        # only recognised through syntax detection, which logs MODULE_TYPELESS_PACKAGE_JSON and
        # reparses the file on every load. The root package.json must stay untyped: setting
        # "type": "module" there would make the CommonJS build load as ESM.
        (out / "dist" / "esm" / "package.json").write_text('{ "type": "module" }\n', encoding="utf-8")
        (out / "dist" / "commonjs" / "package.json").write_text('{ "type": "commonjs" }\n', encoding="utf-8")

        for name in KEEP_ROOT_FILES:
            if (root / name).is_file():
                shutil.copyfile(root / name, out / name)

        vendored = {key: meta[key] for key in PACKAGE_FIELDS if key in meta}
        vendored.update(
            {
                "name": "minimatch",
                "version": version,
                "private": True,
                "description": (
                    f"minimatch {version} runtime with upstream 11.0.1's GHSA-g3hv-75wg-m249 bounds "
                    "backported (Hermes IoT fork vendor copy)"
                ),
                "main": "./compat/index.cjs",
                "module": "./compat/index.mjs",
                "types": "./compat/index.d.cts",
                "exports": {
                    "./package.json": "./package.json",
                    ".": {
                        "import": {"types": "./compat/index.d.ts", "default": "./compat/index.mjs"},
                        "require": {"types": "./compat/index.d.cts", "default": "./compat/index.cjs"},
                    },
                },
                "files": ["dist", "compat", "PROVENANCE.md", "LICENSE", "README.md"],
                # Pinned exactly: the repo-wide supply-chain gate rejects caret ranges in external manifests
                # and the workspace override already pins brace-expansion to this version.
                "dependencies": {"brace-expansion": "5.0.12"},
            }
        )

        (out / "compat").mkdir()
        (out / "compat" / "index.cjs").write_text(COMPAT_CJS, encoding="utf-8")
        (out / "compat" / "index.mjs").write_text(COMPAT_MJS, encoding="utf-8")
        (out / "compat" / "index.d.ts").write_text(COMPAT_DTS, encoding="utf-8")
        (out / "compat" / "index.d.cts").write_text(COMPAT_DCTS, encoding="utf-8")
        # Refuse npm like every other workspace folder (see NPM_REFUSAL): keep the upstream node
        # range and add the unsatisfiable npm entry engine-strict turns into a refusal.
        engines = dict(vendored.get("engines") or {})
        engines["npm"] = NPM_REFUSAL
        vendored["engines"] = engines
        (out / "package.json").write_text(json.dumps(vendored, indent=2) + "\n", encoding="utf-8")

        provenance = [
            f"# minimatch {version} — vendored runtime (Hermes IoT fork)",
            "",
            "Not an official minimatch release. Official source: `isaacs/minimatch` "
            f"v{version}" + (f" (commit `{args.source_commit}`)" if args.source_commit else "") + ".",
            "",
            "## Modifications",
            "",
            "Two resource bounds from upstream **11.0.1** are backported for "
            "`GHSA-g3hv-75wg-m249` / `CVE-2026-118764`:",
            "",
            "1. `firstPhasePreProcess` reads `braceExpandMax` (default 100_000) and stops "
            "growing `**` expansions at the budget.",
            "2. `secondPhasePreProcess` skips the optional quadratic de-duplication above "
            "1000 parts.",
            "",
            "`main`, `module`, `types` and the root `exports` entry point at `compat/`, which keeps "
            "the interface the fork's previous compat tarball exposed: a callable CommonJS module, "
            "and an ESM default (the matcher) plus the named exports, `makeRe` included.",
            "",
            "## Why vendored rather than a tarball dependency",
            "",
            "pnpm `overrides` cannot point a *transitive* dependency at a remote tarball: "
            "`blockExoticSubdeps: true` rejects that on purpose (root dependencies may still be "
            "remote). A local `link:` override keeps the transitive remote surface at zero.",
            "",
            "## Maintenance",
            "",
            "Rebuild with `scripts/ci/build_vendored_minimatch.py --tarball <official tarball> "
            "--out <this directory>` when upstream ships a release the fork must carry. "
            "`tests/ci/test_pnpm_minimatch_compat.py` fails if the lockfile resolves any "
            "`minimatch` below 11.0.1 (the OSV fixed version) outside this directory.",
            "",
        ]
        (out / "PROVENANCE.md").write_text("\n".join(provenance), encoding="utf-8")
        (out / ".npmrc").write_text(NPMRC, encoding="utf-8")

        size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
        print(f"{out}: minimatch {version}, {len(copied)} dist files, {size} bytes total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
