"""The optional dependency and PM refusal gate agree on supported uvloop targets."""
from pathlib import Path
import tomllib

from packaging.markers import Marker, default_environment
from packaging.requirements import Requirement
import pytest


@pytest.mark.parametrize("platform,machine,implementation,supported", [
    ("linux", "armv7l", "CPython", False),
    ("linux", "x86_64", "CPython", True),
    ("darwin", "arm64", "CPython", True),
    ("win32", "AMD64", "CPython", False),
    ("android", "aarch64", "CPython", False),
    ("linux", "x86_64", "PyPy", False),
])
def test_uvloop_selection_and_explicit_gate_agree(platform, machine, implementation, supported):
    root = Path(__file__).resolve().parents[2]
    metadata = tomllib.loads((root / "pyproject.toml").read_text())
    target = {**default_environment(), "sys_platform": platform,
              "platform_machine": machine, "platform_python_implementation": implementation}
    dependencies = metadata["project"]["optional-dependencies"]["uvloop"]
    assert any(Requirement(text).marker.evaluate(target) for text in dependencies) is supported
    gate = metadata["tool"]["hermes"]["extras-platforms"]["uvloop"]
    assert Marker(gate).evaluate(target) is supported
