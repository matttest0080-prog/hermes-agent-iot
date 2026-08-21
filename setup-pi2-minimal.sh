#!/usr/bin/env bash
# ============================================================
# setup-pi2-minimal.sh
# Native-compatible Raspberry Pi 2 / ARMv7 baseline install profile.
# Also safe for newer Raspberry Pi boards, ARM64 SBCs, x86 mini PCs, and VMs.
#
# This script preserves Hermes Agent's upstream Python package path
# (pip install -e .) and only changes the default install profile/config.
# It does NOT patch or delete source files.
#
# Usage:
#   bash setup-pi2-minimal.sh [--profile minimal|iot|rag|full|dev] [--venv ~/.hermes-venv]
#
# Profiles:
#   minimal: smallest practical Hermes CLI install; heavy tools disabled by config
#   iot    : minimal + MCP/ACP/Home Assistant/MQTT/SMS extras
#   rag    : iot + lightweight document/RAG helpers; remote embeddings recommended
#   full   : broader cross-platform Hermes extras for stronger edge hosts
#   dev    : full + developer/test tooling
# ============================================================

set -euo pipefail

PYTHON=${PYTHON:-python3}
VENV_DIR="$HOME/.hermes-venv"
PROFILE="minimal"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage: bash setup-pi2-minimal.sh [--profile minimal|iot|rag|full|dev] [--venv PATH]

Examples:
  bash setup-pi2-minimal.sh
  bash setup-pi2-minimal.sh --profile iot
  bash setup-pi2-minimal.sh --profile rag --venv ~/.hermes-venv
  bash setup-pi2-minimal.sh --profile full    # stronger Pi/ARM64/x86 host only
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    --venv)
      VENV_DIR="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$PROFILE" in
  core) PROFILE="minimal" ;;
  native) PROFILE="iot" ;;
  minimal|iot|rag|full|dev) ;;
  *)
    echo "Invalid profile: $PROFILE (expected minimal, iot, rag, full, or dev)" >&2
    exit 2
    ;;
esac

echo "==> [Pi2] Repository: $REPO_DIR"
echo "==> [Pi2] Profile:    $PROFILE"
echo "==> [Pi2] Venv:       $VENV_DIR"

PY_VERSION="$($PYTHON - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
case "$PY_VERSION" in
  3.11|3.12|3.13) ;;
  *)
    echo "Hermes Agent requires Python >=3.11,<3.14; found $PY_VERSION." >&2
    echo "Install Python 3.11+ first, then rerun this script." >&2
    exit 1
    ;;
esac

if [[ -L "$VENV_DIR" ]]; then
  echo "Refusing symlink virtual environment: $VENV_DIR" >&2
  exit 1
fi
if [[ -e "$VENV_DIR" && ! -d "$VENV_DIR" ]]; then
  echo "Refusing non-directory virtual environment path: $VENV_DIR" >&2
  exit 1
fi
if [[ ! -e "$VENV_DIR" ]]; then
  echo "==> [Pi2] Creating virtual environment"
  (
    umask 077
    mkdir -m 700 -- "$VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
  )
fi

"$PYTHON" - "$VENV_DIR" <<'PY'
import os
import stat
import sys
from pathlib import Path

venv = Path(sys.argv[1])
uid = os.geteuid()

def fail(message):
    raise SystemExit(f"Unsafe virtual environment {venv}: {message}")

def reject_unsafe_mode(path_stat, component):
    if path_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        fail(f"{component} must not be group/world-writable")

venv_stat = os.lstat(venv)
if stat.S_ISLNK(venv_stat.st_mode) or not stat.S_ISDIR(venv_stat.st_mode):
    fail("path must be a real directory, not a symlink")
if venv_stat.st_uid != uid:
    fail(f"directory owner uid {venv_stat.st_uid} does not match current uid {uid}")
reject_unsafe_mode(venv_stat, "venv directory")

for relative, expected_type in (("pyvenv.cfg", stat.S_ISREG), ("bin", stat.S_ISDIR)):
    path = venv / relative
    try:
        path_stat = os.lstat(path)
    except FileNotFoundError:
        fail(f"missing {relative}")
    if stat.S_ISLNK(path_stat.st_mode) or not expected_type(path_stat.st_mode):
        fail(f"{relative} must not be a symlink and has the wrong file type")
    if path_stat.st_uid != uid:
        fail(f"{relative} owner uid {path_stat.st_uid} does not match current uid {uid}")
    reject_unsafe_mode(path_stat, relative)

python_path = venv / "bin" / "python"
if not os.path.lexists(python_path):
    fail("missing bin/python")
try:
    resolved_stat = python_path.resolve(strict=True).stat()
except (OSError, RuntimeError) as exc:
    fail(f"invalid bin/python: {exc}")
if not stat.S_ISREG(resolved_stat.st_mode) or not os.access(python_path, os.X_OK):
    fail("bin/python must resolve to an executable regular file")
PY

# Use the virtualenv's bundled pip. Editable installation resolves exclusively
# from this repository's package metadata instead of a second hand-maintained
# dependency list.

EXTRAS="$PROFILE"

echo "==> [Pi2] Installing Hermes Agent through native package metadata"
LOCK_FILE="$REPO_DIR/requirements/pi2/$PROFILE.lock"
if [[ ! -f "$LOCK_FILE" || -L "$LOCK_FILE" ]]; then
  echo "Missing or unsafe profile lock: $LOCK_FILE" >&2
  exit 1
fi
"$VENV_DIR/bin/python" -m pip install --require-hashes -r "$LOCK_FILE"
"$VENV_DIR/bin/python" -m pip install --no-deps -e "$REPO_DIR[$EXTRAS]"

if [[ "$PROFILE" == "rag" ]]; then
  echo "==> [Pi2] RAG profile uses built-in SQLite/FTS memory and remote-first embeddings"
  echo "    Run document parsing and vector indexing on a central server; no unpinned local packages are installed."
fi

echo "==> [Pi2] Applying profile through the safe no-clobber Python entrypoint"
"$VENV_DIR/bin/python" -m hermes_cli.iot_cli setup --profile "$PROFILE"

if command -v hermes >/dev/null 2>&1; then
  HERMES_CMD="$(command -v hermes)"
else
  HERMES_CMD="$VENV_DIR/bin/hermes"
fi

echo "==> [Pi2] Verifying CLI entrypoint"
"$VENV_DIR/bin/hermes" --help >/dev/null

echo ""
echo "==> Done. Start Hermes with:"
echo "    source '$VENV_DIR/bin/activate'"
echo "    hermes"
echo ""
echo "Optional next steps:"
echo "  - Configure model/provider: hermes setup model"
echo "  - Re-enable disabled tools later: hermes tools"
echo "  - WhatsApp/Baileys bridge and Photon sidecar stay opt-in; review npm audit before enabling"
echo "  - For local llama.cpp/OpenAI-compatible endpoint, set model.provider/custom config via hermes setup"
echo "  - Active hermes command resolved as: $HERMES_CMD"
