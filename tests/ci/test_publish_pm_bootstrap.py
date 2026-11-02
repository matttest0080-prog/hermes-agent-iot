"""The Linux publisher's configured PM tools must have real native artifacts."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from hermes_yaml import safe_load


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.platforms("linux", arch="x86_64")
def test_publisher_pm_selection_passes_native_bootstrap_prepare(tmp_path):
    workflow = safe_load((ROOT / ".github/workflows/publish-pypi.yml").read_text(encoding="utf-8"))
    setup = next(s for s in workflow["jobs"]["build"]["steps"]
                 if s.get("uses") == "./.github/actions/setup-pm")["with"]
    env = dict(os.environ)
    for name in ["GITHUB_ENV", "GITHUB_OUTPUT", "GITHUB_PATH"]:
        env[name] = str(tmp_path / name)
    result = subprocess.run(
        [sys.executable, "-S", str(ROOT / "scripts/ci/setup_toolchain.py"), "prepare",
         "--toolchain", "python", "--packages", setup.get("packages", ""),
         "--extras", setup["extras"], "--home", str(tmp_path / "home")],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    fields = dict(line.split("=", 1) for line in (tmp_path / "GITHUB_OUTPUT").read_text(encoding="utf-8").splitlines())
    assert fields["target"] == "linux-x64"
    assert {"python", "uv"} <= set(json.loads(fields["packages"]))
