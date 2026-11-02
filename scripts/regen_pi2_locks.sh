#!/usr/bin/env bash
# Regenerate hashed ARMv7/ARMv6 locks for the Pi2 installer profiles.
#
# The root uv.lock only covers Python 3.14+ in current upstream releases, while
# this fork supports Python 3.11-3.13 on Pi2. The Python helper resolves each
# profile in an isolated project, preserving existing profile pins where the
# current project metadata does not require a change. It also adds PiWheels
# ARMv6/ARMv7 wheel hashes so pip --require-hashes can select those wheels.
#
# Usage:
#   scripts/regen_pi2_locks.sh                 # rewrite requirements/pi2/*.lock
#   scripts/regen_pi2_locks.sh /tmp/pi2-check  # generate to a scratch directory
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$REPO_DIR/requirements/pi2}"
UV="${UV:-uv}"
export UV

# The generator parses PEP 508 markers. Keep its dependency in a disposable,
# PM-owned tool environment, never in the application's runtime.
"$UV" run --no-project --python 3.12 python - "$REPO_DIR" "$OUT_DIR" <<'PY'
import subprocess
import sys
import tempfile
from pathlib import Path

repo, output = map(Path, sys.argv[1:])
sys.path.insert(0, str(repo))
import pm

with tempfile.TemporaryDirectory(prefix="hermes-pi2-lockgen-tool-") as temp:
    python = pm.ensure_environment(
        "pi2-lockgen", ["packaging==26.2"], root=Path(temp), explicit=True,
    )
    subprocess.run([str(python), str(repo / "scripts/regen_pi2_locks.py"),
                    str(repo), str(output)], check=True)
PY
