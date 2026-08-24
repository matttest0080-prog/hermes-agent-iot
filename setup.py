"""
setup.py — wheel/sdist build guard.

The upstream distribution remains unavailable as a generic wheel. This IoT
fork may additionally build its separately named ``hermes-agent-iot``
distribution only with an explicit release marker. That marker prevents
accidental local artifact creation; it is not an authorization boundary.
Release authorization is enforced by protected Git tags, the GitHub ``pypi``
environment, Trusted Publisher OIDC claims, and immutable Action SHAs.
The lightweight wheel intentionally omits repository-level bundled assets
(skills, optional-skills, optional-mcps, and Desktop/TUI/Web build artifacts),
as documented in README.md and README_PI2.md.

This file overrides the ``bdist_wheel`` and ``sdist`` setuptools commands
to raise an error unless running in Nix or an explicit IoT release build. The PEP 517
``build_wheel`` / ``build_sdist`` hooks in
``setuptools.build_meta`` call these commands internally, so the guard
fires for ``uv build``, ``pip wheel``, ``python -m build``, and direct
``setup.py`` invocations alike.

The one legitimate consumer of ``build_wheel`` is uv2nix, which calls
``setuptools.build_meta.build_wheel`` (→ ``bdist_wheel``) inside a Nix
build sandbox. ``nix/python.nix`` sets ``HERMES_NIX_BUILD=1`` on the
Hermes package derivation, so only that build may create an artifact.

Editable installs (``uv sync``, ``pip install -e .``, ``nix develop``)
use ``build_editable``, which does NOT call ``bdist_wheel`` — it calls
``build_ext`` in editable mode. So the guard does not affect development.
"""

import os

from setuptools import setup
from setuptools.command.sdist import sdist

_IN_NIX_BUILD = os.environ.get("HERMES_NIX_BUILD") == "1"
_IN_IOT_RELEASE_BUILD = os.environ.get("HERMES_IOT_RELEASE_BUILD") == "1"
_BUILD_ALLOWED = _IN_NIX_BUILD or _IN_IOT_RELEASE_BUILD

_BLOCK_MESSAGE = (
    "Building wheels or sdists for hermes-agent-iot is disabled by default.\n"
    "Official IoT release automation must explicitly set HERMES_IOT_RELEASE_BUILD=1.\n"
    "Nix builds remain supported with HERMES_NIX_BUILD=1.\n"
    "\n"
    "If you are developing, use an editable install instead:\n"
    "  uv sync          # or: uv pip install -e .\n"
    "\n"
    "If you are building with Nix (uv2nix), this error should not fire —\n"
    "the Hermes Nix derivation sets HERMES_NIX_BUILD=1. If it does, file a bug."
)


class _GuardedSdist(sdist):
    def run(self, *args, **kwargs):
        if not _BUILD_ALLOWED:
            raise RuntimeError(_BLOCK_MESSAGE)
        return super().run(*args, **kwargs)


cmdclass = {"sdist": _GuardedSdist}

# bdist_wheel is only available when the `wheel` package is installed.
# setuptools.build_meta.build_wheel() calls it internally, so the guard
# fires for all PEP 517 wheel build paths. Define the subclass only when
# the import succeeds — otherwise a None base class raises TypeError at
# class-definition time, before the cmdclass guard can run.
try:
    from setuptools.command.bdist_wheel import bdist_wheel

    class _GuardedBdistWheel(bdist_wheel):
        def run(self, *args, **kwargs):
            if not _BUILD_ALLOWED:
                raise RuntimeError(_BLOCK_MESSAGE)
            return super().run(*args, **kwargs)

    cmdclass["bdist_wheel"] = _GuardedBdistWheel
except ImportError:
    pass

setup(cmdclass=cmdclass)
