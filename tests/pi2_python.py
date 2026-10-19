"""A Python the Pi2 installer accepts, for installer tests.

``setup-pi2-minimal.sh`` refuses interpreters outside Python 3.11–3.13: those are
the versions Raspberry Pi OS ships wheels for, and the guard is deliberate. CI
and developer boxes now run 3.14, so tests that exercise the installer's *other*
guards hand the script a wrapper that reports a supported version and delegates
every real call to the running interpreter. The production guard is untouched.
"""
from __future__ import annotations

import functools
import os
import sys
import tempfile
from pathlib import Path

SUPPORTED = ((3, 11), (3, 12), (3, 13))
REPORTED_VERSION = "3.12"


@functools.cache
def supported_python() -> str:
    """A ``PYTHON`` value ``setup-pi2-minimal.sh`` accepts on any runner."""
    if sys.version_info[:2] in SUPPORTED:
        return sys.executable
    directory = Path(tempfile.mkdtemp(prefix="pi2-supported-python-"))
    wrapper = directory / "python"
    wrapper.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        # The installer reads the major/minor pair from `$PYTHON -` (a heredoc).
        f'if [[ $# -eq 1 && $1 == - ]]; then printf "{REPORTED_VERSION}\\n"; exit 0; fi\n'
        f'exec "{sys.executable}" "$@"\n',
        encoding="utf-8",
    )
    os.chmod(wrapper, 0o700)
    return str(wrapper)
