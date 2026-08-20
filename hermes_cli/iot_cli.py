"""Safe configuration helper for hermes-agent-iot install profiles."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from importlib import metadata, resources
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import Requirement

DISTRIBUTION = "hermes-agent-iot"
PROFILE_TEMPLATES = {
    "minimal": "config.pi2-core.yaml",
    "iot": "config.pi2-native.yaml",
    "rag": "config.pi2-rag.yaml",
    "full": "config.pi2-full.yaml",
    "dev": "config.pi2-full.yaml",
}


def profile_template(profile: str):
    """Return a packaged profile template as an importlib Traversable."""
    return (
        resources.files("hermes_cli")
        .joinpath("resources")
        .joinpath("profiles")
        .joinpath(PROFILE_TEMPLATES[profile])
    )


def _is_virtualenv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix) or hasattr(sys, "real_prefix")


def _normalized(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def _requirements_for_extra(extra: str) -> list[Requirement]:
    """Expand this distribution's self-referencing aggregate extra."""
    dist = metadata.distribution(DISTRIBUTION)
    raw_requirements = dist.requires or []
    pending = [extra]
    visited: set[str] = set()
    requirements: list[Requirement] = []
    environment = default_environment()

    while pending:
        selected = pending.pop()
        if selected in visited:
            continue
        visited.add(selected)
        marker_environment = {**environment, "extra": selected}
        for raw in raw_requirements:
            requirement = Requirement(raw)
            if requirement.marker and not requirement.marker.evaluate(marker_environment):
                continue
            if _normalized(requirement.name) == DISTRIBUTION:
                pending.extend(requirement.extras)
            else:
                requirements.append(requirement)
    return requirements


def _missing_requirements(profile: str) -> list[str]:
    """Return absent or version-incompatible requirements for a profile."""
    try:
        requirements = _requirements_for_extra(profile)
    except metadata.PackageNotFoundError:
        return [f"{DISTRIBUTION} (distribution metadata not installed)"]

    missing: list[str] = []
    for requirement in requirements:
        try:
            installed = metadata.version(requirement.name)
        except metadata.PackageNotFoundError:
            missing.append(str(requirement))
            continue
        if requirement.specifier and not requirement.specifier.contains(installed, prereleases=True):
            missing.append(f"{requirement} (installed {installed})")
    return missing


def _fsync_parent(path: Path) -> None:
    """Durably commit a directory entry where the platform supports it."""
    if os.name == "nt":
        return
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _atomic_private_create(path: Path, content: str) -> tuple[int, int] | None:
    """Create *path* atomically without replacing any existing entry."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            stat_result = os.fstat(stream.fileno())
            identity = stat_result.st_dev, stat_result.st_ino
        try:
            os.link(temporary, path)
        except FileExistsError:
            return None
        _fsync_parent(path)
        return identity
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _home() -> Path:
    return Path(os.environ.get("HERMES_HOME", "").strip() or Path.home() / ".hermes")


def _ensure_private_env(home: Path) -> None:
    """Create an empty profile env file without following or replacing entries."""
    env_path = home / ".env"
    if _atomic_private_create(env_path, "") is None:
        print(f"Existing {env_path} left untouched")
    else:
        print(f"Created empty {env_path}")


def setup_profile(profile: str) -> int:
    if not _is_virtualenv():
        print(
            "hermes-iot setup must run inside a virtual environment; "
            "sudo and system-package overrides are not supported.",
            file=sys.stderr,
        )
        return 2

    missing = _missing_requirements(profile)
    if missing:
        print(
            f"The {profile} dependency set is incomplete. Reinstall inside this virtualenv with:\n"
            f"  {sys.executable} -m pip install '{DISTRIBUTION}[{profile}]'",
            file=sys.stderr,
        )
        for requirement in missing:
            print(f"  missing: {requirement}", file=sys.stderr)
        return 2

    home = _home()
    template = profile_template(profile)
    config = home / "config.yaml"
    record_path = home / "install-profile.json"
    config_exists = os.path.lexists(config)
    if os.path.lexists(record_path) and not config_exists:
        raise FileExistsError(
            f"Existing install-profile record left untouched: {record_path}"
        )
    if config_exists:
        print(f"Existing {config} left untouched")
        print(f"Compare it with packaged template: {template}")
        print("Install-profile record left untouched because the active config was not created by this command")
        if config.is_file() and not config.is_symlink() and (config.stat().st_mode & 0o077):
            print(f"Warning: {config} permissions are broader than 0600", file=sys.stderr)
        _ensure_private_env(home)
        return 0

    config_content = template.read_text(encoding="utf-8")
    config_identity = _atomic_private_create(config, config_content)
    if config_identity is None:
        print(f"Existing {config} left untouched")
        print(f"Compare it with packaged template: {template}")
        print("Install-profile record left untouched because the active config was not created by this command")
        return 0
    print(f"Created {config} from packaged template {template}")
    record = {
        "distribution": DISTRIBUTION,
        "version": metadata.version(DISTRIBUTION),
        "profile": profile,
        "template": template.name,
        "environment": str(sys.prefix),
    }
    try:
        record_identity = _atomic_private_create(
            record_path, json.dumps(record, indent=2) + "\n"
        )
        if record_identity is None:
            raise FileExistsError(
                f"Existing install-profile record left untouched: {record_path}"
            )
    except BaseException:
        # No portable two-path filesystem transaction exists here. Preserve
        # the private no-clobber config rather than risk deleting a path that
        # another process replaced between an identity check and unlink.
        raise
    _ensure_private_env(home)
    return 0


def show_profile() -> int:
    record_path = _home() / "install-profile.json"
    if not record_path.exists():
        print(f"No install profile record found at {record_path}", file=sys.stderr)
        return 1
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read install profile record: {exc}", file=sys.stderr)
        return 1
    for key in ("distribution", "version", "profile", "template", "environment"):
        print(f"{key}: {record.get(key, 'unknown')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-iot")
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("setup", help="Apply an installed IoT package profile")
    setup.add_argument("--profile", required=True, choices=tuple(PROFILE_TEMPLATES))
    profile = commands.add_parser("profile", help="Inspect the package install profile")
    profile_commands = profile.add_subparsers(dest="profile_command", required=True)
    profile_commands.add_parser("show", help="Show the recorded package install profile")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "setup":
        return setup_profile(args.profile)
    return show_profile()


if __name__ == "__main__":
    raise SystemExit(main())
