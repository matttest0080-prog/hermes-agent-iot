import json
from argparse import Namespace
from importlib import metadata

import hermes_cli.main as hermes_main


def test_iot_source_defaults_update_to_pi2_lite(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "hermes-agent-iot"\nversion = "0.20.4"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(hermes_main, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(metadata, "distribution", lambda name: (_ for _ in ()).throw(metadata.PackageNotFoundError(name)))
    monkeypatch.delenv("HERMES_HOME", raising=False)

    assert hermes_main._is_iot_install() is True
    assert hermes_main._resolve_update_branch(Namespace(branch=None)) == "pi2-lite"


def test_iot_install_profile_without_iot_distribution_cannot_redirect_update(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / "install-profile.json").write_text(
        json.dumps({"distribution": "hermes-agent-iot", "profile": "minimal"}),
        encoding="utf-8",
    )
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(hermes_main, "PROJECT_ROOT", project)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(metadata, "distribution", lambda name: (_ for _ in ()).throw(metadata.PackageNotFoundError(name)))

    assert hermes_main._is_iot_install() is False
    assert hermes_main._resolve_update_branch(Namespace(branch="")) == "main"


def test_official_distribution_ignores_stale_user_writable_iot_profile(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    (home / "install-profile.json").write_text(
        json.dumps({"distribution": "hermes-agent-iot", "profile": "minimal"}),
        encoding="utf-8",
    )
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(hermes_main, "PROJECT_ROOT", project)
    monkeypatch.setenv("HERMES_HOME", str(home))

    def installed_distribution(name):
        if name == "hermes-agent":
            return object()
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "distribution", installed_distribution)

    assert hermes_main._is_iot_install() is False
    assert hermes_main._resolve_update_branch(Namespace(branch=None)) == "main"


def test_actual_iot_distribution_defaults_to_pi2_lite(tmp_path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(hermes_main, "PROJECT_ROOT", project)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "home"))

    def installed_distribution(name):
        if name == "hermes-agent-iot":
            return object()
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "distribution", installed_distribution)

    assert hermes_main._is_iot_install() is True
    assert hermes_main._resolve_update_branch(Namespace(branch=None)) == "pi2-lite"


def test_explicit_update_branch_always_wins(monkeypatch):
    monkeypatch.setattr(hermes_main, "_is_iot_install", lambda: True)
    assert hermes_main._resolve_update_branch(Namespace(branch="reviewed-sync")) == "reviewed-sync"


def test_official_install_still_defaults_to_main(monkeypatch):
    monkeypatch.setattr(hermes_main, "_is_iot_install", lambda: False)
    assert hermes_main._resolve_update_branch(Namespace(branch=None)) == "main"
