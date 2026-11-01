#!/usr/bin/env python3
"""Generate the Pi2 hashed requirements locks for Python 3.11-3.13."""
from __future__ import annotations

import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

PROFILES = {
    "minimal": ("minimal",),
    "iot": ("iot",),
    "rag": ("rag",),
    "full": ("full",),
    # The contributor/release profile is full + rag + the dev dependency group.
    "dev": ("full", "rag"),
}
EXCLUDED = {"uvloop", "pillow-heif"}
SELF_REF = re.compile(r"^hermes-agent-iot\[([^]]+)\](?:==[^; ]+)?(?:\s*;.*)?$", re.IGNORECASE)
REQ_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)")
HASH_LINE = re.compile(r"--hash=sha256:([0-9a-f]{64})", re.IGNORECASE)


def canonicalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", requirement)
    return canonicalize(match.group(1)) if match else ""


class LinksParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append((href, ""))

    def handle_data(self, data: str) -> None:
        if self.links and not self.links[-1][1]:
            href, _ = self.links[-1]
            self.links[-1] = (href, data.strip())


def expand_profile(metadata: dict, profile: str) -> list[str]:
    project = metadata["project"]
    extras = project.get("optional-dependencies", {})
    requirements = list(project.get("dependencies", []))
    seen: set[str] = set()

    def add_extra(name: str) -> None:
        name = name.strip().lower()
        if name in seen or name in EXCLUDED:
            return
        seen.add(name)
        for requirement in extras.get(name, []):
            match = SELF_REF.fullmatch(requirement)
            if match:
                for child in match.group(1).split(","):
                    add_extra(child)
            elif requirement_name(requirement) not in EXCLUDED:
                requirements.append(requirement)

    for extra in PROFILES[profile]:
        add_extra(extra)
    if profile == "dev":
        for requirement in metadata.get("dependency-groups", {}).get("dev", []):
            match = SELF_REF.fullmatch(requirement)
            if match:
                for child in match.group(1).split(","):
                    add_extra(child)
            elif requirement_name(requirement) not in EXCLUDED:
                requirements.append(requirement)
    return [req for req in requirements if requirement_name(req) not in EXCLUDED]


def linux_armv7_requirements(requirements: list[str]) -> list[str]:
    """Do not ask the resolver to build inactive Android/Windows source pins."""
    from packaging.markers import default_environment
    from packaging.requirements import Requirement

    targets = [
        {**default_environment(), "sys_platform": "linux", "platform_system": "Linux",
         "platform_machine": "armv7l", "os_name": "posix",
         "platform_python_implementation": "CPython", "implementation_name": "cpython",
         "python_version": version, "python_full_version": version + ".0"}
        for version in ("3.11", "3.12", "3.13")
    ]
    selected = []
    for text in requirements:
        marker = Requirement(text).marker
        # Keep fine-grained patch-version conditions for the universal resolver.
        if marker is None or "python_full_version" in str(marker) or any(
            marker.evaluate(target) for target in targets
        ):
            selected.append(text)
    return selected


def refreshed_dependency_pins(repo: Path, lock: Path, requirements: list[str]) -> dict[str, str]:
    """Refresh only changed direct pins and their closure from the reviewed source lock."""
    old_pins = {
        canonicalize(match.group(1)): match.group(2)
        for line in lock.read_text(encoding="utf-8-sig").splitlines()
        if (match := REQ_LINE.match(line))
    }
    packages = tomllib.loads((repo / "uv.lock").read_text(encoding="utf-8-sig"))["package"]
    by_name: dict[str, list[dict]] = {}
    for package in packages:
        by_name.setdefault(canonicalize(package["name"]), []).append(package)
    pending = [
        canonicalize(match.group(1))
        for requirement in requirements
        if (match := REQ_LINE.match(requirement))
        and old_pins.get(canonicalize(match.group(1))) != match.group(2)
    ]
    # A reviewed direct artifact also owns its dependency closure (not PyPI metadata).
    from packaging.requirements import Requirement
    pending.extend(canonicalize(parsed.name) for text in requirements
                   if (parsed := Requirement(text)).url)
    visited: set[str] = set()
    preferred = {}
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        candidates = by_name.get(name, [])
        versions = {package["version"] for package in candidates}
        # Multiple versions are interpreter/marker splits: let the profile resolver choose.
        if len(versions) == 1:
            preferred[name] = next(iter(versions))
        for package in candidates:
            pending.extend(canonicalize(dep["name"]) for dep in package.get("dependencies", []))
    return preferred


def old_constraints(lock: Path, direct: set[str], preferred: dict[str, str]) -> list[str]:
    constraints = []
    for line in lock.read_text(encoding="utf-8-sig").splitlines():
        match = REQ_LINE.match(line)
        if not match:
            continue
        name = canonicalize(match.group(1))
        if name not in direct and name not in EXCLUDED:
            constraints.append(f"{match.group(1)}=={preferred.get(name, match.group(2))}")
    return constraints


def piwheels_arm_hashes(name: str, version: str, cache: dict[str, list[tuple[str, str]]]) -> set[str]:
    key = canonicalize(name)
    if key not in cache:
        url = f"https://www.piwheels.org/simple/{key}/"
        request = urllib.request.Request(url, headers={"User-Agent": "hermes-pi2-lockgen/1"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                page = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                cache[key] = []
                return set()
            raise
        parser = LinksParser()
        parser.feed(page)
        entries = []
        for href, label in parser.links:
            filename = (label or href.split("#", 1)[0].rsplit("/", 1)[-1]).lower()
            if not filename.endswith(".whl"):
                continue
            if "linux_armv6l" not in filename and "linux_armv7l" not in filename:
                continue
            digest = re.search(r"#sha256=([0-9a-f]{64})", href, re.IGNORECASE)
            if digest:
                entries.append((filename, digest.group(1).lower()))
        cache[key] = entries
    prefix = f"{key.replace('-', '_')}-{version}-".lower()
    return {digest for filename, digest in cache[key] if filename.startswith(prefix)}


def add_piwheels_hashes(lock: Path, cache: dict[str, list[tuple[str, str]]]) -> None:
    lines = lock.read_text(encoding="utf-8-sig").splitlines()
    starts = [i for i, line in enumerate(lines) if REQ_LINE.match(line)]
    output: list[str] = []
    i = 0
    while i < len(lines):
        match = REQ_LINE.match(lines[i])
        if not match:
            output.append(lines[i])
            i += 1
            continue
        end = next((j for j in starts if j > i), len(lines))
        block = lines[i:end]
        name, version = match.groups()
        existing = {m.group(1).lower() for line in block for m in HASH_LINE.finditer(line)}
        extra = sorted(piwheels_arm_hashes(name, version, cache) - existing)
        output.append(lines[i])
        output.extend(f"    --hash=sha256:{digest} \\" for digest in extra)
        output.extend(block[1:])
        i = end
    lock.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: regen_pi2_locks.py REPO_DIR OUT_DIR", file=sys.stderr)
        return 2
    repo, out_dir = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    metadata = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8-sig"))
    uv = os.environ.get("UV", "uv")
    piwheels_cache: dict[str, list[tuple[str, str]]] = {}

    with tempfile.TemporaryDirectory(prefix="hermes-pi2-locks-") as temp:
        staging = Path(temp)
        for profile in PROFILES:
            requirements = linux_armv7_requirements(expand_profile(metadata, profile))
            direct = {requirement_name(req) for req in requirements}
            old_lock = repo / "requirements" / "pi2" / f"{profile}.lock"
            preferred = refreshed_dependency_pins(repo, old_lock, requirements)
            constraints = old_constraints(old_lock, direct, preferred)
            project = staging / profile
            project.mkdir()
            synthetic = (
                "[project]\n"
                f'name = "hermes-pi2-{profile}-lock"\n'
                'version = "0.1.0"\n'
                'requires-python = ">=3.11,<3.14"\n'
                f"dependencies = {json.dumps(requirements)}\n\n"
                "[tool.uv]\n"
                # These locks install on Linux Pi2, not the source-only Android bridge.
                'environments = ["sys_platform == \'linux\'"]\n'
                f"constraint-dependencies = {json.dumps(constraints)}\n"
            )
            (project / "pyproject.toml").write_text(synthetic, encoding="utf-8")
            candidate = staging / f"{profile}.lock"
            print(f"==> resolving Pi2 {profile} (Python 3.11-3.13)", flush=True)
            subprocess.run(
                [uv, "lock", "--project", str(project), "--python", "3.12", "--no-build"],
                check=True,
                timeout=600,
            )
            subprocess.run(
                [
                    uv, "export", "--project", str(project), "--format", "requirements-txt",
                    "--no-header", "--no-emit-project", "--output-file", str(candidate),
                ],
                check=True,
                timeout=600,
            )
            add_piwheels_hashes(candidate, piwheels_cache)

        forbidden = re.compile(r"^(uvloop|pillow-heif)(==|\[| )", re.IGNORECASE)
        leaked = [
            f"{path.name}:{line_no}:{line}"
            for path in staging.glob("*.lock")
            for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1)
            if forbidden.match(line)
        ]
        if leaked:
            raise RuntimeError("excluded package found in generated locks:\n" + "\n".join(leaked))
        out_dir.mkdir(parents=True, exist_ok=True)
        for profile in PROFILES:
            shutil.copy2(staging / f"{profile}.lock", out_dir / f"{profile}.lock")
    print(f"==> Pi2 locks generated and checked in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
