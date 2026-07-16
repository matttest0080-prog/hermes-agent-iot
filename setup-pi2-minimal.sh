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
PROFILE="core"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HERMES_HOME_DIR="${HERMES_HOME:-$HOME/.hermes}"

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

if [[ ! -d "$VENV_DIR" ]]; then
  echo "==> [Pi2] Creating virtual environment"
  "$PYTHON" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Use the virtualenv's bundled pip. Editable installation resolves exclusively
# from this repository's package metadata instead of a second hand-maintained
# dependency list.

case "$PROFILE" in
  minimal)
    EXTRAS="cli,pty"
    ;;
  iot)
    EXTRAS="cli,pty,mcp,acp,homeassistant,mqtt,sms"
    ;;
  rag)
    EXTRAS="cli,pty,mcp,acp,homeassistant,mqtt,sms,honcho"
    ;;
  full)
    EXTRAS="all"
    ;;
  dev)
    EXTRAS="all,dev"
    ;;
esac

echo "==> [Pi2] Installing Hermes Agent through native package metadata"
python -m pip install -e "$REPO_DIR[$EXTRAS]"

if [[ "$PROFILE" == "rag" ]]; then
  echo "==> [Pi2] RAG profile uses built-in SQLite/FTS memory and remote-first embeddings"
  echo "    Run document parsing and vector indexing on a central server; no unpinned local packages are installed."
fi

install -d "$HERMES_HOME_DIR"
case "$PROFILE" in
  minimal) TEMPLATE="$REPO_DIR/templates/config.pi2-core.yaml" ;;
  iot|full|dev) TEMPLATE="$REPO_DIR/templates/config.pi2-native.yaml" ;;
  rag) TEMPLATE="$REPO_DIR/templates/config.pi2-rag.yaml" ;;
esac
if [[ ! -f "$TEMPLATE" ]]; then
  TEMPLATE="$REPO_DIR/templates/config.pi2-core.yaml"
fi

if [[ ! -f "$HERMES_HOME_DIR/config.yaml" ]]; then
  cp "$TEMPLATE" "$HERMES_HOME_DIR/config.yaml"
  chmod 600 "$HERMES_HOME_DIR/config.yaml"
  echo "==> [Pi2] Created $HERMES_HOME_DIR/config.yaml from $(basename "$TEMPLATE")"
else
  echo "==> [Pi2] Existing $HERMES_HOME_DIR/config.yaml left untouched"
  echo "    To apply the Pi2 profile manually, compare with: $TEMPLATE"
fi

if [[ ! -f "$HERMES_HOME_DIR/.env" ]]; then
  touch "$HERMES_HOME_DIR/.env"
  chmod 600 "$HERMES_HOME_DIR/.env"
  echo "==> [Pi2] Created empty $HERMES_HOME_DIR/.env"
fi

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
