#!/usr/bin/env bash
# Backward-compatible entrypoint. The maintained installer is setup-pi2-minimal.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/setup-pi2-minimal.sh" "$@"
