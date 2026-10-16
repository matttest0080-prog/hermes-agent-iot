"""Regression coverage for the Termux broad install profile."""

import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"


def test_pyproject_defines_termux_all_without_known_blockers() -> None:
    text = PYPROJECT.read_text()
    assert "termux-all = [" in text
    assert '"hermes-agent-iot[termux]==0.22.2.post1"' in text
    block = text.split("termux-all = [", 1)[1].split("]", 1)[0]
    assert '"hermes-agent-iot[matrix]' not in block
    assert '"hermes-agent-iot[voice]' not in block
    # No stale self-reference to the upstream distribution name.
    assert "hermes-agent[" not in block
    # The extras stay importable even though install.sh no longer drives them.
    extras = tomllib.loads(text)["project"]["optional-dependencies"]
    assert extras["termux"] and extras["termux-all"]


def test_install_script_rejects_termux_with_the_apt_guidance() -> None:
    text = INSTALL_SH.read_text()
    # Upstream replaced the source-install fallbacks with an explicit Termux guard:
    # the platform is APT-only, so install.sh must fail closed and point at the package.
    assert "pkg install hermes-agent" in text
    assert "unsupported_platform" in text
    assert "TERMUX_VERSION" in text
    assert "*com.termux/files/usr*" in text
    # The retired fork flow (and the constraints file upstream deleted) must not return.
    assert "pip install -e '.[termux-all]'" not in text
    assert "constraints-termux.txt" not in text
    assert "Termux broad profile (.[termux-all]) failed" not in text
    assert "Termux baseline profile (.[termux]) failed" not in text
