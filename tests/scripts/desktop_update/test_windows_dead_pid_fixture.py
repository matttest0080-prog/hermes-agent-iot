"""Native kernel-handle controls for the update tests' exited-process fixture."""
from __future__ import annotations

import subprocess
import sys

import pytest

from tests.scripts.desktop_update.windows_handoff_support import _dead_pid, _ProcessWatch


@pytest.mark.platforms("windows")
def test_dead_pid_remains_an_observable_exited_identity() -> None:
    # Opening this handle fails if the process object has been freed, or sees a
    # live unrelated process if the unreserved numeric pid has been recycled.
    watch = _ProcessWatch(_dead_pid())
    try:
        assert watch.exited_within(0)
    finally:
        watch.close()


@pytest.mark.platforms("windows")
def test_process_watch_distinguishes_live_child_from_exited_child() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"],
                             stdin=subprocess.PIPE)
    watch = _ProcessWatch(child.pid)
    try:
        assert not watch.exited_within(0)
        child.communicate(input=b"", timeout=60)
        assert child.returncode == 0
        assert watch.exited_within(30)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=30)
        watch.close()
