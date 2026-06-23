#!/bin/bash
# ============================================================
# setup-pi2.sh
# Raspberry Pi 2B (ARMv7, 1GB RAM) 最小化安裝腳本
# 用法：bash setup-pi2.sh
# ============================================================

set -e

# Auto-detect Python version (Pi2 might not have 3.10)
# Use python3 without version suffix to ensure compatibility
PYTHON="python3"

# Verify Python version
PYTHON_VERSION=$($PYTHON --version 2>&1 | cut -d' ' -f2)
echo "==> Using Python: $PYTHON_VERSION"

VENV_DIR="$HOME/hermes-venv"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> [Pi2] 建立虛擬環境 ($VENV_DIR)"
$PYTHON -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "==> [Pi2] 升級 pip"
pip install --upgrade pip

echo "==> [Pi2] 安裝核心依賴（不含選用套件）"
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
  ptyprocess \
  chromadb \
  sentence-transformers \
  pypdf \
  beautifulsoup4

echo ""
echo "==> [Pi2] 核心安裝完成。"
echo ""
echo "選用套件（需要時才安裝）："
echo ""
echo "  # Anthropic Claude API"
echo "  pip install anthropic"
echo ""
echo "  # MCP 工具"
echo "  pip install mcp starlette"
echo ""
echo "  # 語音輸入（需要 libportaudio，Pi2 建議先跳過）"
echo "  sudo apt install portaudio19-dev -y"
echo "  pip install sounddevice numpy"
echo "  # faster-whisper 在 ARMv7 需從源碼編譯，不建議"
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
echo "  # Google API 整合"
echo "  pip install google-api-python-client google-auth-oauthlib"
echo ""

# ---- 設定 .env ----
if [ ! -f "$REPO_DIR/.env" ]; then
  if [ -f "$REPO_DIR/.env.example" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    chmod 600 "$REPO_DIR/.env"
    echo "==> .env 已從 .env.example 建立，請填入 API 金鑰"
  fi
fi

# ---- 建立 hermes 指令捷徑 ----
echo "==> [Pi2] 檢查舊版 hermes 指令"
LINK_TARGET="$HOME/.local/bin/hermes"
mkdir -p "$HOME/.local/bin"

# Remove existing files and broken symlinks before writing the wrapper.
# A broken symlink makes -e/-f false but redirection still follows it and fails.
if [ -e "$LINK_TARGET" ] || [ -L "$LINK_TARGET" ]; then
  echo "發現舊版 hermes：$LINK_TARGET"
  if [ -L "$LINK_TARGET" ]; then
    echo "移除符號連結：$LINK_TARGET"
  else
    echo "移除檔案：$LINK_TARGET"
  fi
  rm -f "$LINK_TARGET"
fi

if [ -f "$REPO_DIR/cli.py" ]; then
  cat > "$LINK_TARGET" <<EOF
#!/bin/bash
source "$VENV_DIR/bin/activate"
"$VENV_DIR/bin/python" "$REPO_DIR/cli.py" "\$@"
EOF
  chmod +x "$LINK_TARGET"
  echo "==> 'hermes' 指令已安裝到 $LINK_TARGET"
fi

echo ""
echo "==> 完成！執行 'source ~/.bashrc && hermes' 開始使用"
