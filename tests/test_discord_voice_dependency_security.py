"""Regression tests for the patched Discord voice dependency set.

The Discord recovery paths must not use ``discord.py[voice]`` because
``discord.py==2.7.1`` constrains that extra to vulnerable ``PyNaCl<1.6``.
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
LAZY_DEPS = (REPO_ROOT / "tools" / "lazy_deps.py").read_text(encoding="utf-8")
INSTALL_PS1 = (REPO_ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
VOICE_DOCTOR = (REPO_ROOT / "scripts" / "discord-voice-doctor.py").read_text(
    encoding="utf-8"
)
PI2_INSTALLER = (REPO_ROOT / "setup-pi2-minimal.sh").read_text(encoding="utf-8")

PATCHED_VOICE_SPECS = (
    "discord.py==2.7.1",
    "PyNaCl==1.6.2",
    "davey==0.1.4",
)


def test_all_discord_install_paths_use_patched_voice_specs():
    for spec in PATCHED_VOICE_SPECS:
        assert spec in PYPROJECT
        assert spec in LAZY_DEPS
        assert spec in INSTALL_PS1

    assert "discord.py[voice]" not in PYPROJECT
    assert "discord.py[voice]" not in LAZY_DEPS
    assert "discord.py[voice]" not in INSTALL_PS1


def test_windows_recovery_verifies_every_voice_import():
    for import_name in ("discord", "nacl", "davey"):
        expected = f'Var = "DISCORD_BOT_TOKEN";  Import = "{import_name}"'
        assert expected in INSTALL_PS1


def test_voice_doctor_never_recommends_vulnerable_pynacl_floor():
    assert "PyNaCl>=1.5" not in VOICE_DOCTOR
    assert "need >=1.5" not in VOICE_DOCTOR
    assert "PyNaCl==1.6.2" in VOICE_DOCTOR
    assert "davey==0.1.4" in VOICE_DOCTOR


def test_low_resource_pi2_profiles_do_not_install_discord_voice_stack():
    """ARMv7 has no PyNaCl 1.6.2 wheel; supported Pi2 profiles stay lean."""
    assert 'EXTRAS="cli,pty"' in PI2_INSTALLER
    assert 'EXTRAS="cli,pty,mcp,acp,homeassistant,mqtt,sms"' in PI2_INSTALLER
    assert 'EXTRAS="cli,pty,mcp,acp,homeassistant,mqtt,sms,honcho"' in PI2_INSTALLER
