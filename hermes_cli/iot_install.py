"""Detection of the protected IoT fork install (``hermes-agent-iot``).

Moved out of ``hermes_cli/main.py`` (see its FILE_LINES note): the CLI facade keeps a
re-export so ``hermes_cli.main._is_iot_install`` stays patchable and
``hermes_cli.main_install_repair`` keeps working.
"""

from __future__ import annotations

import logging
from pathlib import Path

from hermes_cli import _startup_fast

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(_startup_fast.project_root_str())


def _is_iot_install() -> bool:
    """Return whether the active source/package is the protected IoT fork.

    Detection is redundant for source vs wheel, but a user-writable
    ``install-profile.json`` alone is not trusted: that file must not redirect
    an official hermes-agent install onto ``pi2-lite``.
    """
    from importlib import metadata as importlib_metadata

    try:
        importlib_metadata.distribution("hermes-agent-iot")
        return True
    except importlib_metadata.PackageNotFoundError:
        pass
    except Exception:
        # Broken metadata (a partly removed install, an unreadable dist-info) must not
        # turn a version check into a crash: log it and probe pyproject.toml instead.
        logger.debug("hermes-agent-iot metadata lookup failed", exc_info=True)

    try:
        import tomllib

        with (PROJECT_ROOT / "pyproject.toml").open("rb") as stream:
            project = tomllib.load(stream).get("project", {})
        return project.get("name") == "hermes-agent-iot"
    except (OSError, ValueError, TypeError):
        return False
