"""Guard the fork's pinned, locally vendored minimatch.

``GHSA-g3hv-75wg-m249`` / ``CVE-2026-118764`` affects every minimatch ``>=7.0.0`` before
``11.0.1``. Upstream 11.0.1 dropped ``makeRe``, so the fork cannot simply take it: it vendors a
10.x runtime with upstream's two resource bounds backported and points the pnpm override at that
one directory with ``link:`` (a remote tarball is what ``blockExoticSubdeps`` rejects for
transitive dependencies). One target covers the whole ``<11`` band, exactly as the fork's
pre-pnpm compat did: every consumer below 11 resolves to the same 10.x-based implementation.

These tests fail closed on the ways that protection can silently disappear:

* the lockfile resolves any minimatch below 11 from the registry again;
* a vendored copy loses one of the backported bounds;
* the override stops covering the band the lock actually uses;
* ``blockExoticSubdeps`` is switched off.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import re
from pathlib import Path

import hermes_yaml as yaml
import pytest

_REPO = Path(__file__).resolve().parents[2]
_VENDOR = _REPO / "vendor"
_LOCK = _REPO / "pnpm-lock.yaml"
_WORKSPACE = _REPO / "pnpm-workspace.yaml"

# Affected: >=7.0.0 <11.0.1. 3.x and 5.x are outside the advisory's range.
_FIRST_AFFECTED = (7, 0, 0)
_FIRST_FIXED = (11, 0, 1)
# OSV fixes GHSA-g3hv-75wg-m249 in 11.0.1, so 11.0.0 is still vulnerable: fail closed below it.

_BACKPORT_MARKERS = (
    "GHSA-g3hv-75wg-m249",
    "globParts.length >= braceExpandMax",
    "if (globParts.length > 1000)",
)

# The override contract: one band, one vendored directory. Every minimatch below 11 in the
# lockfile must resolve to this link; 11.0.1+ may stay on the registry.
_EXPECTED_OVERRIDES = {
    # One target for the whole affected band, as the fork did before the pnpm migration.
    "minimatch@<11": "link:vendor/minimatch-compat-10.2.6",
}


def _version(text: str) -> tuple[int, int, int]:
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", text)
    assert match, f"unparsable version: {text!r}"
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _is_affected(version: str) -> bool:
    parsed = _version(version)
    return _FIRST_AFFECTED <= parsed < _FIRST_FIXED


def _workspace() -> dict:
    return yaml.safe_load(_WORKSPACE.read_text(encoding="utf-8-sig"))


def test_block_exotic_subdeps_stays_on():
    config = _workspace()
    assert config.get("blockExoticSubdeps") is True, (
        "blockExoticSubdeps is the pnpm equivalent of npm's allow-remote=root; the fork keeps it on"
    )


def _minimatch_resolutions() -> list[tuple[str, str]]:
    """Every (where, resolution) pair for minimatch in the lockfile.

    A linked workspace package never gets its own ``packages``/``snapshots`` entry - it only shows
    up as the dependency value that asks for it - so scanning keys alone goes quietly vacuous once
    every consumer is a link. Keys and dependency maps are both collected here.
    """
    lock = yaml.safe_load(_LOCK.read_text(encoding="utf-8-sig"))
    found: list[tuple[str, str]] = []

    def add_deps(where: str, data: object) -> None:
        for dep_section in ("dependencies", "devDependencies", "optionalDependencies"):
            for name, spec in ((data or {}).get(dep_section) or {}).items():
                if name == "minimatch":
                    found.append((where, str(spec)))

    for section in ("packages", "snapshots"):
        for key, value in (lock.get(section) or {}).items():
            name, _, version = str(key).partition("@")
            if name == "minimatch":
                found.append((f"{section} key {key}", version))
            add_deps(f"{section} {key}", value)
    for importer, data in (lock.get("importers") or {}).items():
        add_deps(f"importer {importer}", data)
    return found


def test_every_minimatch_below_11_is_the_single_vendored_link():
    """No consumer below 11.0.1 may keep the registry copy - 3.x/5.x included.

    The fork's pre-pnpm compat replaced every ``minimatch@<11`` consumer with one 10.x-based
    build, and the guard has to say the same thing: the whole band, not just the advisory's
    ``>=7`` slice. 11.0.1 and above are upstream's fixed releases and stay on the registry.
    """
    approved = _EXPECTED_OVERRIDES["minimatch@<11"]
    resolutions = _minimatch_resolutions()
    assert resolutions, "no minimatch resolution found in the lockfile - the guard went vacuous"
    offenders = []
    for where, resolution in resolutions:
        if resolution.startswith(("link:", "file:", "workspace:")):
            if resolution != approved:
                offenders.append(f"{where}: minimatch -> {resolution} (not the approved vendor dir)")
            continue
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", resolution)
        if match and tuple(int(part) for part in match.groups()) < _FIRST_FIXED:
            offenders.append(f"{where}: minimatch@{resolution} (registry, below 11.0.1)")
    assert not offenders, (
        "the lockfile keeps a registry minimatch below 11.0.1:\n  " + "\n  ".join(sorted(offenders))
        + "\nPoint it at vendor/minimatch-compat-10.2.6 (scripts/ci/build_vendored_minimatch.py)."
    )


def test_lock_actually_uses_the_vendored_target():
    """The override must be exercised, not merely declared."""
    approved = _EXPECTED_OVERRIDES["minimatch@<11"]
    links = {resolution for _, resolution in _minimatch_resolutions() if resolution.startswith("link:")}
    assert links == {approved}, f"lock links {sorted(links)} != {{{approved!r}}}"
    consumers = [where for where, resolution in _minimatch_resolutions() if resolution == approved]
    assert len(consumers) > 1, f"only {consumers} resolve through the vendor dir; the override is untested"


@pytest.mark.parametrize("vendor_dir", sorted(p for p in _VENDOR.glob("minimatch-compat-*")))
def test_vendored_runtime_carries_the_backports(vendor_dir: Path):
    meta = json.loads((vendor_dir / "package.json").read_text(encoding="utf-8-sig"))
    assert meta["name"] == "minimatch", meta["name"]
    # 9.x and 10.x carry different upstream licences (ISC before the Blue Oak switch).
    assert meta["license"] in {"ISC", "BlueOak-1.0.0"}, meta["license"]
    assert meta["dependencies"] == {"brace-expansion": "5.0.12"}, meta["dependencies"]
    assert _is_affected(meta["version"]), (
        f"{vendor_dir.name} pins {meta['version']}, which upstream already fixed; drop the vendor dir"
    )
    for entry in ("commonjs", "esm"):
        source = (vendor_dir / "dist" / entry / "index.js").read_text(encoding="utf-8-sig")
        for marker in _BACKPORT_MARKERS:
            assert marker in source, f"{vendor_dir.name}/dist/{entry}/index.js lost: {marker}"


@pytest.mark.parametrize("vendor_dir", sorted(p for p in _VENDOR.glob("minimatch-compat-*")))
def test_vendored_entry_points_and_types_resolve(vendor_dir: Path):
    """Every path the package advertises must exist: a missing .d.ts is a broken type surface."""
    meta = json.loads((vendor_dir / "package.json").read_text(encoding="utf-8-sig"))
    root = meta["exports"]["."]
    declared = {
        "main": meta["main"],
        "module": meta["module"],
        "types": meta["types"],
        "exports.import.types": root["import"]["types"],
        "exports.import.default": root["import"]["default"],
        "exports.require.types": root["require"]["types"],
        "exports.require.default": root["require"]["default"],
    }
    missing = {key: value for key, value in declared.items() if not (vendor_dir / value).is_file()}
    assert not missing, f"{vendor_dir.name}: declared entry point(s) missing: {missing}"

    # The callable interface the fork's previous compat tarball provided must still be advertised.
    assert declared["main"] == "./compat/index.cjs", declared["main"]
    assert declared["module"] == "./compat/index.mjs", declared["module"]
    assert declared["exports.require.default"] == "./compat/index.cjs"
    assert declared["exports.import.default"] == "./compat/index.mjs"

    # Declarations must exist for both module systems and still re-export the engine's types.
    for entry in ("commonjs", "esm"):
        assert (vendor_dir / "dist" / entry / "index.d.ts").is_file()
    assert "export = minimatch" in (vendor_dir / "compat" / "index.d.cts").read_text(encoding="utf-8-sig")
    assert "export { minimatch as default }" in (
        vendor_dir / "compat" / "index.d.ts"
    ).read_text(encoding="utf-8-sig")


def test_vendored_dirs_are_linked_not_published():
    for vendor_dir in _VENDOR.glob("minimatch-compat-*"):
        meta = json.loads((vendor_dir / "package.json").read_text(encoding="utf-8-sig"))
        assert meta.get("private") is True, f"{vendor_dir.name} must stay private"
        assert (vendor_dir / "PROVENANCE.md").is_file(), f"{vendor_dir.name} lacks provenance"
        assert any((vendor_dir / name).is_file() for name in ("LICENSE", "LICENSE.md")), (
            f"{vendor_dir.name} must ship the upstream licence"
        )


def test_vendor_is_a_workspace_project_with_its_dependency_locked():
    """The vendored copy must be a real workspace project, not a bare `link:` directory.

    A `link:` to a directory pnpm does not know as a project installs none of its dependencies:
    the runtime then fails with `Cannot find module 'brace-expansion'`. Listing it under the
    workspace makes pnpm generate an importer for it and install its dependency graph.
    """
    workspace = _workspace()
    assert "vendor/minimatch-compat-*" in (workspace.get("packages") or []), (
        "the vendored package must be a workspace project or its dependencies are never installed"
    )
    lock = yaml.safe_load(_LOCK.read_text(encoding="utf-8-sig"))
    importer = (lock.get("importers") or {}).get("vendor/minimatch-compat-10.2.6")
    assert importer, "no lockfile importer for the vendored package"
    dep = (importer.get("dependencies") or {}).get("brace-expansion")
    assert dep, "the vendored package's brace-expansion dependency is not locked"
    assert dep.get("specifier") == "5.0.12" and dep.get("version") == "5.0.12", dep
    assert "brace-expansion@5.0.12" in (lock.get("packages") or {}), (
        "brace-expansion never reaches the lockfile package set"
    )


def test_vendored_dist_declares_its_module_type():
    """Each dist flavour must carry its own package.json type.

    Node picks a module type from the nearest package.json: without these files the ESM build is
    only discovered by syntax detection (MODULE_TYPELESS_PACKAGE_JSON, plus a reparse per load).
    The root package.json must stay untyped, or the CommonJS build would load as ESM.
    """
    for vendor_dir in sorted(_VENDOR.glob("minimatch-compat-*")):
        root = json.loads((vendor_dir / "package.json").read_text(encoding="utf-8-sig"))
        assert "type" not in root, f"{vendor_dir}: root package.json must not pin a module type"
        esm = json.loads((vendor_dir / "dist" / "esm" / "package.json").read_text(encoding="utf-8-sig"))
        cjs = json.loads((vendor_dir / "dist" / "commonjs" / "package.json").read_text(encoding="utf-8-sig"))
        assert esm == {"type": "module"}, esm
        assert cjs == {"type": "commonjs"}, cjs


def test_loading_the_vendor_logs_no_module_typeless_warning():
    """Load both builds and require a clean stderr."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed; the CI JS lanes cover this")
    for vendor_dir in sorted(_VENDOR.glob("minimatch-compat-*")):
        checks = (
            ("cjs", "const m = require('./dist/commonjs/index.js'); if (typeof m !== 'function' && typeof m.minimatch !== 'function') throw new Error('not callable');"),
            ("esm", "import('./dist/esm/index.js').then((m) => { const api = m.default ?? m; if (typeof api !== 'function' && typeof api.minimatch !== 'function') throw new Error('not callable'); });"),
        )
        for label, script in checks:
            proc = subprocess.run(
                [node, "--input-type=commonjs", "-e", script]
                if label == "cjs"
                else [node, "--input-type=module", "-e", script],
                cwd=vendor_dir,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            assert proc.returncode == 0, f"{vendor_dir} {label}: {proc.stderr}"
            assert "MODULE_TYPELESS_PACKAGE_JSON" not in proc.stderr, (
                f"{vendor_dir} {label}: node had to syntax-detect the module type:\n{proc.stderr}"
            )


def test_vendored_package_refuses_npm_like_every_other_workspace_folder():
    """npm must refuse to build a tree inside the vendored package.

    The vendor directory is a workspace project, so npm sees a standalone package there and would
    resolve it from the registry, past pnpm-workspace.yaml's overrides and release-age gate. The
    repo's contract (tests-js/npm-refused-in-workspaces.test.mjs) is an unsatisfiable
    `engines.npm` plus `engine-strict=true` in the folder's `.npmrc`.
    """
    for vendor_dir in sorted(_VENDOR.glob("minimatch-compat-*")):
        meta = json.loads((vendor_dir / "package.json").read_text(encoding="utf-8-sig"))
        refusal = meta["engines"]["npm"]
        assert "run pnpm install --frozen-lockfile at the repository root" in refusal, meta["engines"]
        # the upstream node range stays: this is about npm, not about dropping support
        assert meta["engines"]["node"] == "18 || 20 || >=22", meta["engines"]
        npmrc = (vendor_dir / ".npmrc").read_text(encoding="utf-8-sig")
        assert "engine-strict=true" in npmrc, npmrc
        assert "build_vendored_minimatch.py" in npmrc, "generated file must point at its source"
