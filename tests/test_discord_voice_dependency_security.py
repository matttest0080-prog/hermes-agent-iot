"""Regression tests for the patched Discord voice dependency set.

The Discord recovery paths must not use ``discord.py[voice]`` because
``discord.py==2.7.1`` constrains that extra to vulnerable ``PyNaCl<1.6``.

Upstream v0.21.7 retired ``tools/lazy_deps.py`` — production code is barred from
importing it (``scripts/ci/check_lazy_deps_imports.py``) and ``pm.ensure_import``
is the only lazy-install surface — and rewrote ``scripts/install.ps1``, dropping
its platform-SDK map. Both were hosts for the voice pins when the fork branched;
the surviving authorities are pyproject.toml's ``messaging`` extra and
``scripts/discord-voice-doctor.py``, which is where this module now pins them.
"""

import importlib.util
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
VOICE_DOCTOR = (REPO_ROOT / "scripts" / "discord-voice-doctor.py").read_text(
    encoding="utf-8"
)
PI2_INSTALLER = (REPO_ROOT / "setup-pi2-minimal.sh").read_text(encoding="utf-8")

# The fork's explicit voice closure lives in the ``messaging`` extra. Upstream's
# bare ``discord`` alias extra still declares ``discord.py[voice]==2.7.1``, but the
# vulnerable ``PyNaCl<1.6`` cap it drags in is neutralised by the ``[tool.uv]``
# override ``pynacl>=1.6,<1.7``; ``messaging`` remains the recovery path, so the
# "never use discord.py[voice]" guarantee is asserted against it (and the doctor).
MESSAGING_EXTRA = tomllib.loads(PYPROJECT)["project"]["optional-dependencies"][
    "messaging"
]

PATCHED_VOICE_SPECS = (
    "discord.py==2.7.1",
    "PyNaCl==1.6.2",
    "davey==0.1.4",
)


def _load_voice_doctor():
    path = REPO_ROOT / "scripts" / "discord-voice-doctor.py"
    spec = importlib.util.spec_from_file_location("discord_voice_doctor", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_surviving_voice_install_authorities_use_patched_specs():
    # Upstream retired tools/lazy_deps.py and rewrote install.ps1 (its SDK map is
    # gone), so the pins' surviving hosts are the messaging extra and the voice
    # doctor. discord.py[voice] must stay out of both recovery paths.
    for spec in PATCHED_VOICE_SPECS:
        assert spec in MESSAGING_EXTRA
        assert spec in VOICE_DOCTOR

    assert not any("discord.py[voice]" in spec for spec in MESSAGING_EXTRA)
    assert "discord.py[voice]" not in VOICE_DOCTOR


def test_voice_doctor_never_recommends_vulnerable_pynacl_floor():
    assert "PyNaCl>=1.5" not in VOICE_DOCTOR
    assert "need >=1.5" not in VOICE_DOCTOR
    assert "PyNaCl==1.6.2" in VOICE_DOCTOR
    assert "davey==0.1.4" in VOICE_DOCTOR


def test_voice_doctor_enforces_pynacl_security_floor():
    doctor = _load_voice_doctor()
    assert not doctor._pynacl_version_is_secure("1.5.0")
    assert not doctor._pynacl_version_is_secure("1.6.1")
    assert doctor._pynacl_version_is_secure("1.6.2")
    assert doctor._pynacl_version_is_secure("1.7.0")
    assert not doctor._pynacl_version_is_secure("unknown")


def test_low_resource_pi2_profiles_do_not_install_discord_voice_stack():
    """ARMv7 has no PyNaCl 1.6.2 wheel; supported Pi2 profiles stay lean."""
    project = tomllib.loads(PYPROJECT)["project"]
    extras = project["optional-dependencies"]
    core_names = {
        canonicalize_name(Requirement(spec).name)
        for spec in project["dependencies"]
    }

    def dependency_names(profile):
        names = set(core_names)
        visited = set()

        def visit(extra):
            if extra in visited:
                return
            visited.add(extra)
            for spec in extras[extra]:
                requirement = Requirement(spec)
                name = canonicalize_name(requirement.name)
                if name == "hermes-agent-iot":
                    for nested in requirement.extras:
                        visit(nested)
                else:
                    names.add(name)

        visit(profile)
        return names

    forbidden = {"discord-py", "pynacl", "davey"}
    for profile in ("minimal", "iot", "rag"):
        assert dependency_names(profile).isdisjoint(forbidden)

    # The installer delegates profile expansion to pyproject.toml instead of
    # maintaining a second dependency list that can drift from wheel metadata.
    assert 'EXTRAS="$PROFILE"' in PI2_INSTALLER
