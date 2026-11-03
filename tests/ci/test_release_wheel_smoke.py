"""Artifact probes must not see source modules before the wheel is installed."""
import os
from pathlib import Path
import subprocess
import sys
import venv

from scripts.ci.smoke_release_wheel import isolated_environment, venv_python


ROOT = Path(__file__).resolve().parents[2]


def test_clean_venv_rejects_checkout_import_despite_setup_pm_pythonpath(tmp_path):
    environment = tmp_path / "venv"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = venv_python(environment)
    parent = dict(os.environ, PYTHONPATH=str(ROOT), VIRTUAL_ENV=str(ROOT / ".venv"),
                  HERMES_PYTHON=sys.executable)
    parent.pop("PYTHONHOME", None)
    probe = "import importlib.util; assert importlib.util.find_spec('hermes_cli') is None"
    # Real interpreter + real checkout: inherited setup-pm PYTHONPATH makes an
    # empty environment falsely see Hermes. No fake installed METADATA involved.
    poisoned = subprocess.run([str(python), "-c", probe], cwd=tmp_path, env=parent,
                              capture_output=True, text=True, timeout=60, check=False)
    assert poisoned.returncode != 0, "negative control must expose checkout visibility"
    assert "AssertionError" in poisoned.stderr, poisoned.stderr
    clean = isolated_environment(tmp_path, environment, parent)
    result = subprocess.run([str(python), "-c", probe], cwd=tmp_path, env=clean,
                            capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stderr
    assert parent["PYTHONPATH"] == str(ROOT), "do not mutate the caller's environment"


def test_artifact_environment_owns_python_and_home_without_leaking_source(tmp_path):
    target = tmp_path / "target"
    parent = {"PYTHONPATH": str(ROOT), "PYTHONHOME": str(ROOT),
              "VIRTUAL_ENV": str(ROOT), "HERMES_PYTHON": sys.executable,
              "HERMES_HOME": str(ROOT), "HERMES_RUNTIME_DIR": str(ROOT),
              "PATH": os.defpath, "CI": "true"}
    clean = isolated_environment(tmp_path, target, parent)
    assert "PYTHONPATH" not in clean and "PYTHONHOME" not in clean
    assert clean["HERMES_PYTHON"] == str(venv_python(target))
    assert clean["VIRTUAL_ENV"] == str(target)
    assert clean["HERMES_HOME"] == str(tmp_path / "home")
    assert clean["HERMES_RUNTIME_DIR"] == str(tmp_path / "runtime")
    assert clean["PATH"].split(os.pathsep)[0] == str(venv_python(target).parent)
    assert clean["CI"] == parent["CI"]
