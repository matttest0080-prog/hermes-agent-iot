#!/bin/bash
# ============================================================
# setup-pi2-minimal.sh
# Minimal install script for Raspberry Pi 2B (ARMv7, 1GB RAM)
# Usage: bash setup-pi2-minimal.sh
# ============================================================

set -e

PYTHON=python3
VENV_DIR="$HOME/.hermes-venv"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> [Pi2] Creating virtual environment ($VENV_DIR)"
$PYTHON -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "==> [Pi2] Upgrading pip"
pip install --upgrade pip

echo "==> [Pi2] Installing core dependencies (optional packages excluded)"
pip install \
  openai==2.24.0 \
  certifi \
  python-dotenv \
  fire \
  "httpx[socks]" \
  rich \
  tenacity \
  pyyaml \
  ruamel.yaml \
  requests \
  jinja2 \
  pydantic \
  prompt_toolkit \
  croniter \
  packaging \
  Markdown \
  "PyJWT[crypto]" \
  "urllib3>=2.7.0,<3" \
  psutil \
  websockets \
  pathspec \
  ptyprocess

echo ""
echo "==> [Pi2] Core installation completed."
echo ""
echo "Optional packages (install only when needed):"
echo ""
echo "  # RAG support (cloud memory; honcho-ai replaces chromadb to avoid local vector storage on Pi2)"
echo "  pip install honcho-ai pypdf beautifulsoup4"
echo "  # Set HONCHO_API_KEY in .env"
echo "  # Request a honcho-ai key at: https://honcho.dev"
echo ""
echo "  # Anthropic Claude API"
echo "  pip install anthropic"
echo ""
echo "  # MCP tools"
echo "  pip install mcp starlette"
echo ""
echo "  # Voice input (requires libportaudio; recommended to skip on Pi2)"
echo "  sudo apt install portaudio19-dev -y"
echo "  pip install sounddevice numpy"
echo "  # faster-whisper requires source compilation on ARMv7; not recommended"
echo ""
echo "  # Telegram Bot"
echo "  pip install 'python-telegram-bot[webhooks]'"
echo ""
echo "  # Slack Bot"
echo "  pip install slack-bolt slack-sdk aiohttp"
echo ""
echo "  # Web API (FastAPI)"
echo "  pip install fastapi 'uvicorn[standard]'"
echo ""
echo "  # Google API integrations"
echo "  pip install google-api-python-client google-auth-oauthlib"
echo ""

# ---- Configure .env ----
if [ ! -f "$REPO_DIR/.env" ]; then
  if [ -f "$REPO_DIR/.env.example" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    chmod 600 "$REPO_DIR/.env"
    echo "==> Created .env from .env.example; please fill in API keys"
  fi
fi

# ---- Check and remove old hermes command ----
echo "==> [Pi2] Checking old hermes command"
LINK_TARGET="$HOME/.local/bin/hermes"
install -d "$HOME/.local/bin"

# Use -e OR -L: a broken symlink makes -e/-f false but still breaks
# redirection ("No such file or directory") because the shell follows it.
if [ -e "$LINK_TARGET" ] || [ -L "$LINK_TARGET" ]; then
  echo "Found old hermes command: $LINK_TARGET"
  if [ -L "$LINK_TARGET" ]; then
    echo "Removing symlink: $LINK_TARGET"
  else
    echo "Removing file: $LINK_TARGET"
  fi
  rm -f "$LINK_TARGET"
fi

# ---- Create hermes command wrapper ----
if [ -f "$REPO_DIR/cli.py" ]; then
  cat > "$LINK_TARGET" <<EOF
#!/bin/bash
source "$VENV_DIR/bin/activate"
"$VENV_DIR/bin/python" "$REPO_DIR/cli.py" "\$@"
EOF
  chmod +x "$LINK_TARGET"
  echo "==> Installed 'hermes' command at $LINK_TARGET"
else
  echo "Warning: cli.py not found; skipping hermes command creation"
fi

echo ""
echo "==> Fixing plugins.browser import issue (Pi2 does not need cloud browsers)"
if [ -f "$REPO_DIR/fix-browser-import.sh" ]; then
  bash "$REPO_DIR/fix-browser-import.sh"
elif [ -f "$REPO_DIR/tools/browser_tool.py" ]; then
  python3 - <<'PYEOF'
import sys, os
os.chdir(os.environ.get("REPO_DIR", "."))

with open("tools/browser_tool.py", "r", encoding="utf-8") as f:
    content = f.read()

old = 'from plugins.browser.browserbase.provider import ('
new = 'try:\n    from plugins.browser.browserbase.provider import ('

if old in content and 'try:\n    from plugins.browser' not in content:
    for pkg, cls in [
        ("browserbase", "BrowserbaseBrowserProvider as BrowserbaseProvider"),
        ("browser_use", "BrowserUseBrowserProvider as BrowserUseProvider"),
        ("firecrawl",   "FirecrawlBrowserProvider as FirecrawlProvider"),
    ]:
        old_imp = f"from plugins.browser.{pkg}.provider import (\n    {cls},\n)"
        new_imp = (f"try:\n"
                   f"    from plugins.browser.{pkg}.provider import (\n"
                   f"        {cls},\n"
                   f"    )\n"
                   f"except ImportError:\n"
                   f"    {cls.split(' as ')[-1]} = None")
        content = content.replace(old_imp, new_imp)
    with open("tools/browser_tool.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("browser_tool.py has been fixed")
PYEOF
fi

echo ""
echo "==> Done! Run 'source ~/.bashrc && hermes' to start"
