"""Install a release wheel outside the checkout and verify the actual installation."""
from __future__ import annotations

import argparse
import email
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


PUBLIC_PROFILES = frozenset({"minimal", "iot", "rag", "full"})


def validate_public_extras(extras: set[str]) -> None:
    if not PUBLIC_PROFILES <= extras:
        raise ValueError("wheel is missing supported public profiles")


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def isolated_environment(work: Path, venv: Path, parent: dict[str, str]) -> dict[str, str]:
    # setup-pm exports PYTHONPATH for source tests. In an artifact smoke it makes
    # pip see checkout egg-info as installed and skip the actual wheel entirely.
    env = {key: value for key, value in parent.items()
           if key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "HERMES_PYTHON"}}
    python = venv_python(venv)
    env.update({
        "VIRTUAL_ENV": str(venv), "HERMES_PYTHON": str(python),
        "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
        "HERMES_HOME": str(work / "home"),
        "HERMES_RUNTIME_DIR": str(work / "runtime"),
        "BH_HOME": str(work / "browser-home"),
        "PATH": str(python.parent) + os.pathsep + env.get("PATH", ""),
    })
    return env


# Run in the installed interpreter, not this helper's source/test environment.
INSPECT_INSTALL = r'''
import json, sys
from importlib import metadata, resources
from pathlib import Path
import hermes_cli
version, digest, required_extras = sys.argv[1:]
prefix = Path(sys.prefix).resolve()
dist = metadata.distribution("hermes-agent-iot")
assert dist.version == version, dist.version
assert Path(hermes_cli.__file__).resolve().is_relative_to(prefix), hermes_cli.__file__
assert Path(dist.locate_file("")).resolve().is_relative_to(prefix)
origin = json.loads(dist.read_text("direct_url.json"))
assert origin["archive_info"]["hashes"]["sha256"] == digest, origin
extras = set(dist.metadata.get_all("Provides-Extra") or [])
assert set(json.loads(required_extras)) <= extras
root = resources.files("hermes_cli").joinpath("resources", "profiles")
assert sorted(p.name for p in root.iterdir()) == [
    "config.pi2-core.yaml", "config.pi2-full.yaml",
    "config.pi2-native.yaml", "config.pi2-rag.yaml",
]
assert metadata.version("browser-harness-hermes-compat") == "0.1.13.post1"
assert metadata.distribution("browser-harness-hermes-compat").read_text("direct_url.json") is None
try:
    metadata.distribution("browser-harness")
except metadata.PackageNotFoundError:
    pass
else:
    raise AssertionError("official browser distribution must not coexist")
print("Installed wheel origin, namespace, extras and resources verified:", version, digest)
'''


def smoke(wheel: Path, tag: str) -> dict[str, str]:
    wheel = wheel.resolve(strict=True)
    with zipfile.ZipFile(wheel) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise ValueError("expected one wheel distribution")
        metadata = email.message_from_bytes(archive.read(names[0]))
    version = str(metadata["Version"])
    if metadata["Name"] != "hermes-agent-iot" or tag != f"iot-v{version}":
        raise ValueError("tag, wheel name and version must agree")
    validate_public_extras(set(metadata.get_all("Provides-Extra") or []))
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="hermes-release-smoke-") as directory:
        work = Path(directory)
        venv = work / "venv"
        env = isolated_environment(work, venv, dict(os.environ))
        subprocess.run([sys.executable, "-I", "-m", "venv", str(venv)],
                       cwd=work, env=env, check=True, timeout=180)
        python = venv_python(venv)
        subprocess.run([str(python), "-I", "-m", "pip", "install", f"{wheel}[minimal]"],
                       cwd=work, env=env, check=True, timeout=1200)
        subprocess.run([str(python), "-I", "-m", "pip", "check"],
                       cwd=work, env=env, check=True, timeout=120)
        for command in ("hermes-iot", "hermes"):
            executable = python.parent / (command + (".exe" if os.name == "nt" else ""))
            subprocess.run([str(executable), "--help"], cwd=work, env=env,
                           check=True, timeout=180)
        subprocess.run([str(python), "-I", "-c", INSPECT_INSTALL, version, digest,
                        json.dumps(sorted(PUBLIC_PROFILES))],
                       cwd=work, env=env, check=True, timeout=120)
    return {"tag": tag, "version": version, "wheel": wheel.name, "sha256": digest,
            "scope": "fresh minimal wheel installation, not a public registry or device validation"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    receipt = json.dumps(smoke(args.wheel, args.tag), indent=2) + "\n"
    print(receipt)
    if args.receipt:
        args.receipt.write_text(receipt, encoding="utf-8")


if __name__ == "__main__":
    main()
