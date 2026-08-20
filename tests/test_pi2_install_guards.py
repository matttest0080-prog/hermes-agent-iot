from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def write_minimal_repo(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        """
[project]
dependencies = [
  "fastapi>=0.104.0,<1",
  "uvicorn>=0.24.0,<1",
]

[project.optional-dependencies]
web = ["fastapi==0.133.1", "uvicorn==0.41.0"]
mqtt = ["paho-mqtt==2.1.0"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "tools").mkdir()
    (root / "tools" / "lazy_deps.py").write_text(
        'LAZY_DEPS = {"tool.dashboard": ("fastapi==0.133.1", "uvicorn==0.41.0"), "tool.mqtt": ("paho-mqtt==2.1.0",)}\n',
        encoding="utf-8",
    )
    (root / "hermes_cli").mkdir()
    (root / "hermes_cli" / "web_server.py").write_text(
        'config = uvicorn.Config(app, host="127.0.0.1", port=9119, loop="asyncio")\n',
        encoding="utf-8",
    )
    (root / "setup-pi2.sh").write_text(
        """
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/setup-pi2-minimal.sh" "$@"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (root / "setup-pi2-minimal.sh").write_text(
        """
#!/usr/bin/env bash
os.lstat(venv)
os.path.lexists(python_path)
stat.S_IWGRP | stat.S_IWOTH
pip install --require-hashes -r "$LOCK_FILE"
pip install --no-deps -e "$REPO_DIR[$EXTRAS]"
"$VENV_DIR/bin/python" -m hermes_cli.iot_cli setup --profile "$PROFILE"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    templates = root / "templates"
    templates.mkdir()
    for name, floor in {
        "config.pi2-core.yaml": 2048,
        "config.pi2-native.yaml": 8192,
        "config.pi2-rag.yaml": 8192,
        "config.pi2-full.yaml": 65536,
    }.items():
        (templates / name).write_text(
            f"agent:\n  minimum_tool_context_length: {floor}\n",
            encoding="utf-8",
        )


class Pi2InstallGuardTests(unittest.TestCase):
    def run_guard(self, repo: Path, *, no_site: bool = False) -> subprocess.CompletedProcess[str]:
        script = Path(__file__).resolve().parents[1] / "scripts" / "check_pi2_install_guards.py"
        command = [sys.executable]
        if no_site:
            command.append("-S")
        command.extend([str(script), "--repo", str(repo)])
        return subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
        )

    def run_installer(self, venv: Path) -> subprocess.CompletedProcess[str]:
        script = Path(__file__).resolve().parents[1] / "setup-pi2-minimal.sh"
        return subprocess.run(
            ["bash", str(script), "--venv", str(venv)],
            check=False,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHON": sys.executable},
        )

    def test_existing_venv_rejects_group_or_world_writable_security_components(self) -> None:
        cases = (
            ("venv directory", Path("."), 0o720),
            ("venv directory", Path("."), 0o702),
            ("bin", Path("bin"), 0o720),
            ("bin", Path("bin"), 0o702),
            ("pyvenv.cfg", Path("pyvenv.cfg"), 0o620),
            ("pyvenv.cfg", Path("pyvenv.cfg"), 0o602),
        )
        for label, relative, mode in cases:
            with self.subTest(component=label, mode=oct(mode)), tempfile.TemporaryDirectory() as tmp:
                venv = Path(tmp) / "venv"
                (venv / "bin").mkdir(parents=True)
                (venv / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
                python_path = venv / "bin" / "python"
                python_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                python_path.chmod(0o700)
                venv.chmod(0o700)
                (venv / "bin").chmod(0o700)
                (venv / "pyvenv.cfg").chmod(0o600)
                (venv / relative).chmod(mode)

                result = self.run_installer(venv)

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Unsafe virtual environment", result.stderr)
            self.assertIn(label, result.stderr)
            self.assertIn("group/world-writable", result.stderr)

    def test_new_venv_creation_uses_safe_modes_with_permissive_caller_umask(self) -> None:
        source_script = Path(__file__).resolve().parents[1] / "setup-pi2-minimal.sh"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            script = repo / "setup-pi2-minimal.sh"
            script.write_text(source_script.read_text(encoding="utf-8"), encoding="utf-8")
            lock_dir = repo / "requirements" / "pi2"
            lock_dir.mkdir(parents=True)
            (lock_dir / "minimal.lock").write_text("", encoding="utf-8")
            fake_python = repo / "fake-python"
            fake_python.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ $# -eq 1 && $1 == - ]]; then printf '3.11\\n'; exit 0; fi\n"
                f"if [[ $1 == - ]]; then exec {sys.executable!s} \"$@\"; fi\n"
                "if [[ $1 == -m && $2 == venv ]]; then\n"
                "  mkdir -p \"$3/bin\"\n"
                "  printf 'home = /usr/bin\\n' > \"$3/pyvenv.cfg\"\n"
                "  printf '#!/bin/sh\\nexit 0\\n' > \"$3/bin/python\"\n"
                "  printf '#!/bin/sh\\nexit 0\\n' > \"$3/bin/hermes\"\n"
                "  chmod 700 \"$3/bin/python\" \"$3/bin/hermes\"\n"
                "  exit 0\n"
                "fi\n"
                "exit 2\n",
                encoding="utf-8",
            )
            fake_python.chmod(0o700)
            venv = repo / "venv"

            result = subprocess.run(
                ["bash", "-c", 'umask 0002; exec bash "$1" --venv "$2"', "test", str(script), str(venv)],
                check=False,
                text=True,
                capture_output=True,
                env={**os.environ, "PYTHON": str(fake_python)},
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for component in (venv, venv / "bin", venv / "pyvenv.cfg"):
                self.assertEqual(component.stat().st_mode & 0o022, 0, component)

    def test_pi2_install_guard_accepts_lightweight_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_minimal_repo(repo)

            result = self.run_guard(repo)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Pi2 install guard checks passed", result.stdout)

    def test_pi2_install_guard_has_no_third_party_runtime_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_minimal_repo(repo)

            result = self.run_guard(repo, no_site=True)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Pi2 install guard checks passed", result.stdout)

    def test_pi2_install_guard_requires_venv_permission_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_minimal_repo(repo)
            setup = repo / "setup-pi2-minimal.sh"
            setup.write_text(
                setup.read_text(encoding="utf-8").replace("stat.S_IWGRP | stat.S_IWOTH\n", ""),
                encoding="utf-8",
            )

            result = self.run_guard(repo)

        self.assertEqual(result.returncode, 1)
        self.assertIn("group/world-writable virtualenv components", result.stdout)

    def test_pi2_install_guard_blocks_uvicorn_standard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_minimal_repo(repo)
            pyproject = repo / "pyproject.toml"
            pyproject.write_text(
                pyproject.read_text(encoding="utf-8").replace("uvicorn==0.41.0", "uvicorn[standard]==0.41.0"),
                encoding="utf-8",
            )

            result = self.run_guard(repo)

        self.assertEqual(result.returncode, 1)
        self.assertIn("uvicorn[standard]", result.stdout)
        self.assertIn("pyproject.toml", result.stdout)

    def test_pi2_install_guard_blocks_legacy_unlocked_installer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_minimal_repo(repo)
            (repo / "setup-pi2.sh").write_text(
                "#!/usr/bin/env bash\npip install openai pyyaml beautifulsoup4\n",
                encoding="utf-8",
            )

            result = self.run_guard(repo)

        self.assertEqual(result.returncode, 1)
        self.assertIn("setup-pi2-minimal.sh", result.stdout)
        self.assertIn("deprecated wrapper", result.stdout)

    def test_pi2_wrapper_rejects_common_package_install_invocations(self) -> None:
        invocations = (
            "pip install pyyaml",
            "pip3 install pyyaml",
            "python -m pip install pyyaml",
            "python3 -m pip install pyyaml",
            "command pip install pyyaml",
        )
        for invocation in invocations:
            with self.subTest(invocation=invocation), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                write_minimal_repo(repo)
                (repo / "setup-pi2.sh").write_text(
                    "#!/usr/bin/env bash\n"
                    "set -euo pipefail\n"
                    f"{invocation}\n"
                    "SCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"\n"
                    "exec \"$SCRIPT_DIR/setup-pi2-minimal.sh\" \"$@\"\n",
                    encoding="utf-8",
                )

                result = self.run_guard(repo)

            self.assertEqual(result.returncode, 1)
            self.assertIn("only contain strict mode", result.stdout)

    def test_pi2_install_guard_requires_asyncio_loop_even_if_comment_mentions_uvloop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_minimal_repo(repo)
            web_server = repo / "hermes_cli" / "web_server.py"
            web_server.write_text(
                "# Avoid uvloop on Pi2.\nconfig = uvicorn.Config(app, host='127.0.0.1', port=9119)\n",
                encoding="utf-8",
            )

            result = self.run_guard(repo)

        self.assertEqual(result.returncode, 1)
        self.assertIn('loop="asyncio"', result.stdout)

    def test_pi2_install_guard_requires_sqlite_vec_opt_in_on_armv7(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_minimal_repo(repo)
            (repo / "setup-pi2-minimal.sh").write_text(
                "#!/usr/bin/env bash\npython -m pip install sqlite-vec\n",
                encoding="utf-8",
            )

            result = self.run_guard(repo)

        self.assertEqual(result.returncode, 1)
        self.assertIn("HERMES_PI2_TRY_SQLITE_VEC", result.stdout)

    def test_pi2_install_guard_rejects_untrusted_activate_and_shell_config_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            write_minimal_repo(repo)
            (repo / "setup-pi2-minimal.sh").write_text(
                "#!/usr/bin/env bash\n"
                'source "$VENV_DIR/bin/activate"\n'
                'python -m pip install -e "$REPO_DIR[$EXTRAS]"\n'
                'cp "$TEMPLATE" "$HERMES_HOME_DIR/config.yaml"\n'
                'touch "$HERMES_HOME_DIR/.env"\n',
                encoding="utf-8",
            )

            result = self.run_guard(repo)

        self.assertEqual(result.returncode, 1)
        self.assertIn("untrusted virtualenv activate", result.stdout)
        self.assertIn("safe no-clobber Python entrypoint", result.stdout)

    def test_real_pi2_templates_use_active_cli_platform_toolsets(self) -> None:
        import yaml

        from hermes_cli.tools_config import _get_platform_tools

        repo = Path(__file__).resolve().parents[1]
        expected_mqtt = {
            "config.pi2-core.yaml": False,
            "config.pi2-native.yaml": True,
            "config.pi2-rag.yaml": True,
            "config.pi2-full.yaml": False,
        }

        for name, mqtt_enabled in expected_mqtt.items():
            with self.subTest(profile=name):
                config = yaml.safe_load((repo / "templates" / name).read_text(encoding="utf-8"))
                self.assertNotIn("toolsets", config, "legacy top-level toolsets key is ignored")
                self.assertIn("cli", config.get("platform_toolsets", {}))
                resolved = _get_platform_tools(config, "cli")
                self.assertEqual("mqtt" in resolved, mqtt_enabled)
                if name == "config.pi2-full.yaml":
                    self.assertEqual(config["agent"]["minimum_tool_context_length"], 65_536)
                    self.assertNotIn("disabled_toolsets", config["agent"])

        setup_text = (repo / "setup-pi2-minimal.sh").read_text(encoding="utf-8")
        self.assertIn(
            'hermes_cli.iot_cli setup --profile "$PROFILE"',
            setup_text,
        )
        self.assertNotIn('source "$VENV_DIR/bin/activate"', setup_text)
    def test_low_resource_profiles_have_local_llama_fallback(self) -> None:
        import yaml

        repo = Path(__file__).resolve().parents[1]
        for name in ("config.pi2-core.yaml", "config.pi2-native.yaml", "config.pi2-rag.yaml"):
            with self.subTest(profile=name):
                config = yaml.safe_load((repo / "templates" / name).read_text(encoding="utf-8"))
                fallback = config["fallback_providers"]
                self.assertEqual(len(fallback), 1)
                self.assertEqual(fallback[0]["provider"], "custom")
                self.assertEqual(fallback[0]["model"], "pi2-local")
                self.assertEqual(fallback[0]["base_url"], "http://127.0.0.1:8080/v1")
                self.assertEqual(fallback[0]["api_key"], "local")


if __name__ == "__main__":
    unittest.main()
