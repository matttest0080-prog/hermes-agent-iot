#!/usr/bin/env python3
"""Guard Raspberry Pi 2 install paths against heavy or ARMv7-hostile deps.

This check is intentionally narrow: explanatory documentation may mention
packages such as uvloop or chromadb, but Pi2 install metadata, lazy deps,
setup scripts, and runtime dashboard startup must keep the default path light.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
import tomllib
from pathlib import Path
from typing import Iterable

BANNED_DEFAULT_DEPS = (
    "uvicorn[standard]",
    "uvloop",
    "torch",
    "sentence-transformers",
    "chromadb",
    # No armv7/armv6 wheel; pip falls back to a source build needing libheif
    # headers, which fails and takes the whole install down with it.
    "pillow-heif",
)

# uvloop is the one banned package that stays reachable on purpose: upstream gates it
# behind its own [uvloop] extra, and the fork's all/full profiles pull that extra in so
# desktop/server hosts get the faster loop. Pi2 and Termux profiles must never reach it —
# there is no armv7 wheel, and libuv does not build on Termux. The two tuples below are
# asserted in both directions so a future upstream sync cannot silently widen or narrow
# the policy.
UVLOOP_EXTRA = "uvloop"
UVLOOP_OPT_IN_PROFILES = ("all", "full")
UVLOOP_FREE_PROFILES = ("minimal", "iot", "rag", "termux", "termux-all")

# Packages the hashed Pi2 locks (requirements/pi2/*.lock) must never list: they are
# consumed by `pip install --require-hashes` on armv7/armv6, where these have no wheel.
# Keep in sync with EXCLUDED_PACKAGES in scripts/regen_pi2_locks.sh.
PI2_UNINSTALLABLE_PACKAGES = ("uvloop", "pillow-heif")


class FailureCollector:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def add(self, message: str) -> None:
        self.failures.append(message)

    def exit_code(self) -> int:
        return 1 if self.failures else 0

    def report(self) -> None:
        if not self.failures:
            print("Pi2 install guard checks passed")
            return
        print("Pi2 install guard checks failed:")
        for failure in self.failures:
            print(f"- {failure}")


def normalize_dep(dep: str) -> str:
    dep = dep.strip().lower()
    # Remove environment markers and common version specifiers for prefix checks.
    dep = dep.split(";", 1)[0].strip()
    return re.split(r"\s*(?:==|>=|<=|~=|!=|>|<)", dep, maxsplit=1)[0].strip()


def iter_pyproject_deps(pyproject: Path) -> Iterable[tuple[str, str]]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8-sig"))
    project = data.get("project", {})
    for dep in project.get("dependencies", []) or []:
        yield "project.dependencies", dep
    optional = project.get("optional-dependencies", {}) or {}
    for extra, deps in optional.items():
        for dep in deps or []:
            yield f"project.optional-dependencies.{extra}", dep


def check_pyproject(repo: Path, failures: FailureCollector) -> None:
    pyproject = repo / "pyproject.toml"
    if not pyproject.exists():
        failures.add("pyproject.toml is missing")
        return

    for section, dep in iter_pyproject_deps(pyproject):
        package = normalize_dep(dep)
        if package in BANNED_DEFAULT_DEPS:
            if package == "uvloop" and section == f"project.optional-dependencies.{UVLOOP_EXTRA}":
                # The opt-in extra is the only sanctioned home for uvloop; who may reach
                # it is enforced by check_uvloop_profile_policy().
                continue
            failures.add(
                f"pyproject.toml {section} contains Pi2-hostile dependency {dep!r}; "
                "use lightweight/remote alternatives by default"
            )


def extra_closure(optional: dict, roots: Iterable[str]) -> set[str]:
    """Transitive closure of profile extras, following ``hermes-agent-iot[a,b]`` pins."""
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        extra = stack.pop()
        if extra in seen:
            continue
        seen.add(extra)
        for dep in optional.get(extra, []) or []:
            for reference in re.findall(r"hermes-agent(?:-iot)?\[([^\]]+)\]", dep):
                stack.extend(part.strip() for part in reference.split(",") if part.strip())
    return seen


def check_uvloop_profile_policy(repo: Path, failures: FailureCollector) -> None:
    """minimal/iot/rag/termux* must stay uvloop-free; all/full must keep it reachable."""
    pyproject = repo / "pyproject.toml"
    if not pyproject.exists():
        return
    data = tomllib.loads(pyproject.read_text(encoding="utf-8-sig"))
    optional = (data.get("project", {}) or {}).get("optional-dependencies", {}) or {}

    def uvloop_via(profile: str) -> str:
        for extra in extra_closure(optional, [profile]):
            for dep in optional.get(extra, []) or []:
                if normalize_dep(dep) == UVLOOP_EXTRA:
                    return extra
        return ""

    for profile in UVLOOP_FREE_PROFILES:
        if profile not in optional:
            continue
        via = uvloop_via(profile)
        if via:
            failures.add(
                f"pyproject.toml profile {profile!r} must not install uvloop "
                f"(reached through extra {via!r}); only {'/'.join(UVLOOP_OPT_IN_PROFILES)} may"
            )

    for profile in UVLOOP_OPT_IN_PROFILES:
        if profile not in optional:
            continue
        if not uvloop_via(profile):
            failures.add(
                f"pyproject.toml profile {profile!r} should install uvloop through the "
                f"{UVLOOP_EXTRA!r} extra; add hermes-agent-iot[{UVLOOP_EXTRA}] back or record why not"
            )


def check_pi2_locks(repo: Path, failures: FailureCollector) -> None:
    """Hashed Pi2 locks must only list packages an armv7/armv6 host can install."""
    locks_dir = repo / "requirements" / "pi2"
    if not locks_dir.is_dir():
        return
    locks = sorted(locks_dir.glob("*.lock"))
    if not locks:
        failures.add(
            "requirements/pi2 holds no *.lock files; setup-pi2-minimal.sh would have nothing to install"
        )
        return
    for lock in locks:
        for number, line in enumerate(lock.read_text(encoding="utf-8-sig").splitlines(), 1):
            match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\]+)", line)
            if match and match.group(1).lower() in PI2_UNINSTALLABLE_PACKAGES:
                failures.add(
                    f"{lock.relative_to(repo)}:{number} lists {match.group(1)!r}, which Pi2 "
                    "profiles must not install; regenerate with scripts/regen_pi2_locks.sh"
                )


def iter_python_string_literals(path: Path) -> Iterable[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except SyntaxError as exc:
        raise SystemExit(f"Could not parse {path}: {exc}") from exc
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value


def check_lazy_deps(repo: Path, failures: FailureCollector) -> None:
    lazy_deps = repo / "tools" / "lazy_deps.py"
    if not lazy_deps.exists():
        failures.add("tools/lazy_deps.py is missing")
        return

    for literal in iter_python_string_literals(lazy_deps):
        package = normalize_dep(literal)
        if package in BANNED_DEFAULT_DEPS:
            failures.add(
                f"tools/lazy_deps.py contains Pi2-hostile lazy dependency {literal!r}; "
                "dashboard lazy deps must use plain uvicorn and avoid local ML/RAG stacks"
            )


def check_setup_pi2(repo: Path, failures: FailureCollector) -> None:
    setup = repo / "setup-pi2.sh"
    if not setup.exists():
        failures.add("setup-pi2.sh is missing")
        return

    text = setup.read_text(encoding="utf-8-sig")
    commands = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "#!"))
    ]
    valid_wrapper = (
        len(commands) == 3
        and commands[0] == "set -euo pipefail"
        and commands[1].startswith("SCRIPT_DIR=")
        and commands[2].startswith("exec ")
        and "setup-pi2-minimal.sh" in commands[2]
        and '"$@"' in commands[2]
    )
    if not valid_wrapper:
        failures.add(
            "setup-pi2.sh deprecated wrapper must only contain strict mode, "
            "SCRIPT_DIR resolution, and exec of setup-pi2-minimal.sh"
        )


def check_setup_pi2_minimal(repo: Path, failures: FailureCollector) -> None:
    setup = repo / "setup-pi2-minimal.sh"
    if not setup.exists():
        failures.add("setup-pi2-minimal.sh is missing")
        return

    text = setup.read_text(encoding="utf-8-sig")
    if re.search(r"(?m)^\s*(?:source|\.)\s+.*bin/activate", text):
        failures.add(
            "setup-pi2-minimal.sh must not source an untrusted virtualenv activate script"
        )

    required_security_markers = {
        "os.lstat(venv)": "lstat validation for the existing virtualenv",
        "os.path.lexists(python_path)": "lexists validation for virtualenv bin/python",
        "stat.S_IWGRP | stat.S_IWOTH": "rejection of group/world-writable virtualenv components",
        'pip install --require-hashes -r "$LOCK_FILE"': "hashed dependency install exported from uv.lock",
        'pip install --no-deps -e': "metadata-driven project install without dependency re-resolution",
        'hermes_cli.iot_cli setup --profile "$PROFILE"': "safe no-clobber Python entrypoint for config and .env",
    }
    for marker, purpose in required_security_markers.items():
        if marker not in text:
            failures.add(f"setup-pi2-minimal.sh is missing {purpose}")

    if "sqlite-vec" in text:
        required_markers = ("HERMES_PI2_TRY_SQLITE_VEC", "armv7l", "armv6l")
        missing = [marker for marker in required_markers if marker not in text]
        if missing:
            failures.add(
                "setup-pi2-minimal.sh installs sqlite-vec without the Pi2 opt-in/ARM guard; "
                f"missing {', '.join(missing)}"
            )


def check_iot_optional_deps(repo: Path, failures: FailureCollector) -> None:
    """Keep IoT extras useful but out of the Pi2/core dependency path."""
    pyproject = repo / "pyproject.toml"
    if not pyproject.exists():
        return
    data = tomllib.loads(pyproject.read_text(encoding="utf-8-sig"))
    project = data.get("project", {})
    deps = project.get("dependencies", []) or []
    optional = project.get("optional-dependencies", {}) or {}
    core_packages = {normalize_dep(dep) for dep in deps}
    if "paho-mqtt" in core_packages:
        failures.add("paho-mqtt must stay out of project.dependencies; MQTT should remain optional/lazy on Pi2")
    mqtt_extra = {normalize_dep(dep) for dep in optional.get("mqtt", []) or []}
    if "paho-mqtt" not in mqtt_extra:
        failures.add("pyproject.toml should expose optional-dependencies.mqtt with paho-mqtt")

    # Upstream retired tools/lazy_deps for production code: pm.ensure_import is the only
    # lazy-install surface (scripts/ci/check_lazy_deps_imports.py blocks the old stub), so the
    # MQTT tool must reach its extra through pm instead of the retired registry.
    mqtt_tool = repo / "tools" / "mqtt_tool.py"
    if mqtt_tool.exists():
        mqtt_text = mqtt_tool.read_text(encoding="utf-8-sig")
        if 'ensure_import("mqtt")' not in mqtt_text:
            failures.add(
                "tools/mqtt_tool.py should lazy-install paho-mqtt through pm.ensure_import(\"mqtt\")"
            )
        # Match real import statements only: prose/comments may name the retired module.
        retired_imports = (
            "from tools.lazy_deps import",
            "from tools.lazy_deps.",
            "import tools.lazy_deps",
        )
        if any(marker in mqtt_text for marker in retired_imports):
            failures.add("tools/mqtt_tool.py must not import the retired lazy-install registry")
    else:
        failures.add("tools/mqtt_tool.py is missing; MQTT must stay an optional Pi2 tool")


def check_pi2_context_templates(repo: Path, failures: FailureCollector) -> None:
    """Guard the low-resource context-floor optimization using stdlib only."""
    expected = {
        "config.pi2-core.yaml": 2048,
        "config.pi2-native.yaml": 8192,
        "config.pi2-rag.yaml": 8192,
        "config.pi2-full.yaml": 65536,
    }

    for filename, expected_floor in expected.items():
        path = repo / "templates" / filename
        if not path.exists():
            failures.add(f"{path.relative_to(repo)} is missing")
            continue
        text = path.read_text(encoding="utf-8-sig")
        agent_match = re.search(r"(?ms)^agent:\s*\n(?P<body>(?:^[ \t]+.*(?:\n|$))*)", text)
        body = agent_match.group("body") if agent_match else ""
        floor_match = re.search(
            r"(?m)^[ \t]+minimum_tool_context_length:\s*([0-9]+)\s*(?:#.*)?$",
            body,
        )
        actual = int(floor_match.group(1)) if floor_match else None
        if actual != expected_floor:
            failures.add(
                f"{path.relative_to(repo)} agent.minimum_tool_context_length should be "
                f"{expected_floor}, got {actual!r}"
            )


def check_web_server(repo: Path, failures: FailureCollector) -> None:
    web_server = repo / "hermes_cli" / "web_server.py"
    if not web_server.exists():
        failures.add("hermes_cli/web_server.py is missing")
        return

    text = web_server.read_text(encoding="utf-8-sig")
    compact = re.sub(r"\s+", "", text)
    if "uvicorn.Config" in text and 'loop="asyncio"' not in compact and "loop='asyncio'" not in compact:
        failures.add(
            'hermes_cli/web_server.py must pass loop="asyncio" to uvicorn.Config so Pi2/ARMv7 never auto-selects uvloop'
        )

    for literal in iter_python_string_literals(web_server):
        package = normalize_dep(literal)
        if package in ("uvicorn[standard]", "uvloop"):
            failures.add(
                f"hermes_cli/web_server.py user-facing install/runtime string contains {literal!r}; "
                "Pi2 guidance should use plain uvicorn"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Repository root to check")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    failures = FailureCollector()
    check_pyproject(repo, failures)
    check_uvloop_profile_policy(repo, failures)
    check_pi2_locks(repo, failures)
    check_lazy_deps(repo, failures)
    check_setup_pi2(repo, failures)
    check_setup_pi2_minimal(repo, failures)
    check_iot_optional_deps(repo, failures)
    check_pi2_context_templates(repo, failures)
    check_web_server(repo, failures)
    failures.report()
    return failures.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
