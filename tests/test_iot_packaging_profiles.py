import json
import os
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def metadata():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_distribution_version_scripts_and_aggregate_extras():
    from hermes_cli import __release_date__, __version__

    project = metadata()["project"]
    assert project["name"] == "hermes-agent-iot"
    assert project["version"] == "0.20.5.post2"
    assert __version__ == project["version"]
    assert __release_date__ == "2026.8.24"
    assert project["scripts"]["hermes-iot"] == "hermes_cli.iot_cli:main"
    assert {"hermes", "hermes-agent", "hermes-acp"} <= project["scripts"].keys()
    extras = project["optional-dependencies"]
    assert extras["minimal"] == ["hermes-agent-iot[cli,pty]==0.20.5.post2"]
    assert extras["iot"] == ["hermes-agent-iot[minimal,mcp,acp,homeassistant,mqtt,sms]==0.20.5.post2"]
    assert extras["rag"] == ["hermes-agent-iot[iot,honcho]==0.20.5.post2"]
    assert extras["full"] == ["hermes-agent-iot[all]==0.20.5.post2"]
    assert "hermes-agent-iot[full]==0.20.5.post2" in extras["dev"]
    assert "pytest==9.1.1" in extras["dev"]
    assert extras["vercel"] == ["vercel==0.7.2"]
    from tools.lazy_deps import LAZY_DEPS
    assert LAZY_DEPS["terminal.vercel"] == ("vercel==0.7.2",)
    assert metadata()["tool"]["uv"]["exclude-newer-package"]["vercel"] is False
    for profile in ("minimal", "iot", "rag"):
        assert "vercel" not in " ".join(extras[profile]).lower()
    assert {item["extra"] for group in metadata()["tool"]["uv"]["conflicts"] for item in group} >= {
        "modal", "vercel"
    }
    all_specs = [s for values in extras.values() for s in values]
    assert not any("hermes-agent[" in spec for spec in all_specs)


def test_vercel_recovery_guidance_uses_the_locked_sdk_version():
    doctor = (ROOT / "hermes_cli" / "doctor.py").read_text(encoding="utf-8")
    assert "python -m pip install vercel==0.7.2" in doctor
    assert "python -m pip install vercel)" not in doctor
    assert 'python -m pip install vercel"' not in doctor


def test_profile_templates_are_packaged_and_dev_reuses_full():
    from hermes_cli.iot_cli import profile_template

    expected = {
        "minimal": "config.pi2-core.yaml",
        "iot": "config.pi2-native.yaml",
        "rag": "config.pi2-rag.yaml",
        "full": "config.pi2-full.yaml",
        "dev": "config.pi2-full.yaml",
    }
    for profile, name in expected.items():
        resource = profile_template(profile)
        assert resource.name == name
        assert "minimum_tool_context_length" in resource.read_text(encoding="utf-8")


def _run_cli(tmp_path, *args, extra_env=None, installed_distributions=()):
    env = os.environ.copy()
    env["HERMES_HOME"] = str(tmp_path / "home")
    if installed_distributions:
        metadata_site = tmp_path / "metadata-site"
        metadata_site.mkdir()
        for name, version in installed_distributions:
            dist_info = metadata_site / f"{name.replace('-', '_')}-{version}.dist-info"
            dist_info.mkdir()
            (dist_info / "METADATA").write_text(
                f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n\n",
                encoding="utf-8",
            )
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = os.pathsep.join(
            value for value in (str(metadata_site), existing_pythonpath) if value
        )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "hermes_cli.iot_cli", *args],
        cwd=ROOT, env=env, text=True, capture_output=True, check=False,
    )


def test_setup_atomically_creates_private_config_and_secret_free_manifest(tmp_path):
    result = _run_cli(
        tmp_path,
        "setup",
        "--profile",
        "iot",
        installed_distributions=(("paho-mqtt", "2.1.0"),),
    )
    assert result.returncode == 0, result.stderr
    home = tmp_path / "home"
    config = home / "config.yaml"
    manifest = home / "install-profile.json"
    assert config.exists() and manifest.exists()
    if os.name != "nt":
        assert config.stat().st_mode & 0o777 == 0o600
        assert manifest.stat().st_mode & 0o777 == 0o600
    data = json.loads(manifest.read_text())
    assert data == {
        "distribution": "hermes-agent-iot",
        "version": "0.20.5.post2",
        "profile": "iot",
        "template": "config.pi2-native.yaml",
        "environment": str(sys.prefix),
    }
    assert not any(word in manifest.read_text().lower() for word in ("secret", "token", "password", "api_key"))


def test_setup_never_overwrites_existing_config(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    config = home / "config.yaml"
    config.write_text("user: value\n", encoding="utf-8")
    result = _run_cli(
        tmp_path,
        "setup",
        "--profile",
        "rag",
        installed_distributions=(
            ("paho-mqtt", "2.1.0"),
            ("honcho-ai", "2.2.0"),
        ),
    )
    assert result.returncode == 0
    assert config.read_text() == "user: value\n"
    assert not (home / "install-profile.json").exists()
    assert "left untouched" in result.stdout
    assert "config.pi2-rag.yaml" in result.stdout


def test_setup_rejects_non_virtualenv_and_missing_dependencies(tmp_path, monkeypatch, capsys):
    from hermes_cli import iot_cli

    monkeypatch.setattr(iot_cli, "_is_virtualenv", lambda: False)
    assert iot_cli.setup_profile("minimal") == 2
    assert "virtual environment" in capsys.readouterr().err

    monkeypatch.setattr(iot_cli, "_is_virtualenv", lambda: True)
    monkeypatch.setattr(iot_cli, "_missing_requirements", lambda profile: ["paho-mqtt==2.1.0"])
    assert iot_cli.setup_profile("iot") == 2
    error = capsys.readouterr().err
    assert "dependency set is incomplete" in error
    assert "paho-mqtt==2.1.0" in error


def test_no_environment_variable_can_bypass_profile_checks():
    source = (ROOT / "hermes_cli" / "iot_cli.py").read_text(encoding="utf-8")
    assert "HERMES_IOT_TEST_" not in source


def test_record_write_failure_keeps_private_config_without_record(tmp_path, monkeypatch):
    from hermes_cli import iot_cli

    home = tmp_path / "home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(iot_cli, "_is_virtualenv", lambda: True)
    monkeypatch.setattr(iot_cli, "_missing_requirements", lambda profile: [])
    real_create = iot_cli._atomic_private_create

    def fail_record(path, content):
        if path.name == "install-profile.json":
            raise OSError("injected record failure")
        return real_create(path, content)

    monkeypatch.setattr(iot_cli, "_atomic_private_create", fail_record)
    with pytest.raises(OSError, match="injected record failure"):
        iot_cli.setup_profile("minimal")
    assert (home / "config.yaml").exists()
    assert stat.S_IMODE((home / "config.yaml").stat().st_mode) == 0o600
    assert not (home / "install-profile.json").exists()


def test_existing_record_is_never_overwritten_and_config_is_not_created(
    tmp_path, monkeypatch
):
    from hermes_cli import iot_cli

    home = tmp_path / "home"
    home.mkdir()
    record = home / "install-profile.json"
    record.write_text('{"profile":"legacy"}\n', encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(iot_cli, "_is_virtualenv", lambda: True)
    monkeypatch.setattr(iot_cli, "_missing_requirements", lambda profile: [])
    with pytest.raises(FileExistsError, match="left untouched"):
        iot_cli.setup_profile("minimal")
    assert record.read_text(encoding="utf-8") == '{"profile":"legacy"}\n'
    assert not (home / "config.yaml").exists()


def test_atomic_create_never_replaces_existing_entry(tmp_path):
    from hermes_cli.iot_cli import _atomic_private_create

    target = tmp_path / "config.yaml"
    target.write_text("created-by-other-process\n", encoding="utf-8")
    assert _atomic_private_create(target, "new-content\n") is None
    assert target.read_text(encoding="utf-8") == "created-by-other-process\n"


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics require POSIX")
def test_atomic_create_never_follows_dangling_symlink(tmp_path):
    from hermes_cli.iot_cli import _atomic_private_create

    outside = tmp_path / "outside.yaml"
    target = tmp_path / "config.yaml"
    target.symlink_to(outside)

    assert _atomic_private_create(target, "new-content\n") is None
    assert target.is_symlink()
    assert not outside.exists()


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics require POSIX")
def test_existing_record_symlink_is_never_followed_or_replaced(tmp_path, monkeypatch):
    from hermes_cli import iot_cli

    home = tmp_path / "home"
    home.mkdir()
    outside = tmp_path / "outside-record.json"
    outside.write_text('{"profile":"external"}\n', encoding="utf-8")
    record = home / "install-profile.json"
    record.symlink_to(outside)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(iot_cli, "_is_virtualenv", lambda: True)
    monkeypatch.setattr(iot_cli, "_missing_requirements", lambda profile: [])

    with pytest.raises(FileExistsError, match="left untouched"):
        iot_cli.setup_profile("minimal")

    assert record.is_symlink()
    assert outside.read_text(encoding="utf-8") == '{"profile":"external"}\n'
    assert not (home / "config.yaml").exists()


@pytest.mark.skipif(os.name == "nt", reason="symlink semantics require POSIX")
def test_setup_never_follows_dangling_config_or_env_symlinks(
    tmp_path, monkeypatch, capsys
):
    from hermes_cli import iot_cli

    home = tmp_path / "home"
    home.mkdir()
    outside_config = tmp_path / "outside-config.yaml"
    outside_env = tmp_path / "outside.env"
    (home / "config.yaml").symlink_to(outside_config)
    (home / ".env").symlink_to(outside_env)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(iot_cli, "_is_virtualenv", lambda: True)
    monkeypatch.setattr(iot_cli, "_missing_requirements", lambda profile: [])

    assert iot_cli.setup_profile("minimal") == 0
    output = capsys.readouterr().out

    assert (home / "config.yaml").is_symlink()
    assert (home / ".env").is_symlink()
    assert not outside_config.exists()
    assert not outside_env.exists()
    assert not (home / "install-profile.json").exists()
    assert f"Existing {home / '.env'} left untouched" in output


@pytest.mark.skipif(os.name == "nt", reason="installer is a POSIX shell script")
def test_pi_installer_rejects_symlinked_venv_without_sourcing_activate(tmp_path):
    target = tmp_path / "attacker-venv"
    (target / "bin").mkdir(parents=True)
    marker = tmp_path / "activate-was-sourced"
    (target / "bin" / "activate").write_text(
        f"touch {marker}\nexit 77\n", encoding="utf-8"
    )
    (target / "pyvenv.cfg").write_text("home = /attacker\n", encoding="utf-8")
    venv = tmp_path / "venv"
    venv.symlink_to(target, target_is_directory=True)

    result = subprocess.run(
        [
            "bash",
            str(ROOT / "setup-pi2-minimal.sh"),
            "--profile",
            "minimal",
            "--venv",
            str(venv),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHON": sys.executable, "HERMES_HOME": str(tmp_path / "home")},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "symlink" in result.stderr.lower()
    assert not marker.exists()


def test_atomic_create_reports_directory_fsync_failure_without_clobber(tmp_path, monkeypatch):
    from hermes_cli import iot_cli

    target = tmp_path / "config.yaml"
    monkeypatch.setattr(
        iot_cli,
        "_fsync_parent",
        lambda path: (_ for _ in ()).throw(OSError("injected fsync failure")),
    )
    with pytest.raises(OSError, match="injected fsync failure"):
        iot_cli._atomic_private_create(target, "content\n")
    assert target.read_text(encoding="utf-8") == "content\n"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_setup_race_leaves_config_and_record_untouched(tmp_path, monkeypatch, capsys):
    from hermes_cli import iot_cli

    home = tmp_path / "home"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(iot_cli, "_is_virtualenv", lambda: True)
    monkeypatch.setattr(iot_cli, "_missing_requirements", lambda profile: [])

    def competing_create(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("competing-config\n", encoding="utf-8")
        return None

    monkeypatch.setattr(iot_cli, "_atomic_private_create", competing_create)
    assert iot_cli.setup_profile("minimal") == 0
    assert (home / "config.yaml").read_text(encoding="utf-8") == "competing-config\n"
    assert not (home / "install-profile.json").exists()
    assert "left untouched" in capsys.readouterr().out


def test_setup_subprocess_rejects_unsatisfied_profile_dependency(tmp_path):
    result = _run_cli(
        tmp_path,
        "setup",
        "--profile",
        "iot",
        installed_distributions=(("paho-mqtt", "0.0.0"),),
    )

    assert result.returncode != 0
    assert "paho-mqtt==2.1.0" in result.stderr
    assert not (tmp_path / "home" / "config.yaml").exists()
    assert not (tmp_path / "home" / "install-profile.json").exists()


def test_missing_requirements_checks_every_constraint(monkeypatch):
    from hermes_cli import iot_cli

    monkeypatch.setattr(
        iot_cli,
        "_requirements_for_extra",
        lambda profile: [
            iot_cli.Requirement("packaging>=20"),
            iot_cli.Requirement("packaging<1"),
        ],
    )
    missing = iot_cli._missing_requirements("minimal")
    assert len(missing) == 1
    assert "packaging<1" in missing[0]


def test_profile_show_reports_install_record(tmp_path):
    assert _run_cli(tmp_path, "setup", "--profile", "dev").returncode == 0
    result = _run_cli(tmp_path, "profile", "show")
    assert result.returncode == 0
    for value in ("hermes-agent-iot", "0.20.5.post2", "dev", "config.pi2-full.yaml", str(sys.prefix)):
        assert value in result.stdout


def test_invalid_profile_is_nonzero(tmp_path):
    result = _run_cli(tmp_path, "setup", "--profile", "bogus")
    assert result.returncode != 0
