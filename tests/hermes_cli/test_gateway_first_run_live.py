"""First-run guidance without an executor when the operator opted out of the free tier."""
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("argv", [[], ["chat"], ["-z", "hello"]])
def test_headless_first_run_exits_with_setup_guidance_before_gateway(tmp_path, argv):
    home = tmp_path / "state"
    home.mkdir(mode=0o700)
    # The default free tier now is a valid executor. Opt out explicitly to test
    # the no-executor guidance without contacting an external provisioning service.
    (home / "config.yaml").write_text("nous: {guest: false}\n", encoding="utf-8")
    user = tmp_path / "user"
    user.mkdir()
    root = Path(__file__).resolve().parents[2]
    tools = tmp_path / "bin"
    tools.mkdir()
    gh = tools / ("gh.cmd" if os.name == "nt" else "gh")
    gh.write_text("@exit /b 1\n" if os.name == "nt" else "#!/bin/sh\nexit 1\n", encoding="utf-8")
    gh.chmod(0o700)
    env = {k: os.environ[k] for k in ("PATH", "LANG", "TZ") if k in os.environ}
    # A host keyring-backed gh login must not make this no-executor fixture ready.
    env["PATH"] = str(tools) + os.pathsep + env.get("PATH", "")
    env.update(HOME=str(user), USERPROFILE=str(user), HERMES_HOME=str(home),
               PYTHONPATH=str(root), PYTHONUNBUFFERED="1")
    result = subprocess.run(
        [sys.executable, "-m", "hermes_cli.main", *argv], cwd=tmp_path, env=env,
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=40, check=False
    )
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "hermes config set model.provider custom" in result.stdout
    assert "Run setup now?" not in result.stdout
    assert "Session:" not in result.stderr
    assert not (home / "gateway.pid").exists()
    assert not (home / "state.db").exists()
