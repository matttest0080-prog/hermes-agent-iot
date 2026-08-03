from __future__ import annotations

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
python -m pip install -e "$REPO_DIR[$EXTRAS]"
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
            'full|dev) TEMPLATE="$REPO_DIR/templates/config.pi2-full.yaml"',
            setup_text,
        )
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
