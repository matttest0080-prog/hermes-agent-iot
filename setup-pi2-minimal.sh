#!/bin/bash
# ============================================================
# setup-pi2-minimal.sh
# Raspberry Pi 2B (ARMv7, 1GB RAM) 最小化安裝腳本
# 用法：bash setup-pi2-minimal.sh
# ============================================================

set -e

PYTHON=python3
VENV_DIR="$HOME/.hermes-venv"
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
  ptyprocess

echo ""
echo "==> [Pi2] 核心安裝完成。"
echo ""
echo "選用套件（需要時才安裝）："
echo ""
echo "  # RAG 功能（雲端記憶體，honcho-ai 取代 chromadb，Pi2 省去本機向量庫）"
echo "  pip install honcho-ai pypdf beautifulsoup4"
echo "  # 需在 .env 填入 HONCHO_API_KEY"
echo "  # honcho-ai 官網申請：https://honcho.dev"
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

# ---- 檢查並清除舊版 hermes ----
echo "==> [Pi2] 檢查舊版 hermes 指令"
if [ -f "$HOME/.local/bin/hermes" ]; then
  echo "發現舊版 hermes：$HOME/.local/bin/hermes"
  if [ -L "$HOME/.local/bin/hermes" ]; then
    echo "移除符號連結：$HOME/.local/bin/hermes"
    rm -f "$HOME/.local/bin/hermes"
  else
    echo "移除檔案：$HOME/.local/bin/hermes"
    rm -f "$HOME/.local/bin/hermes"
  fi
fi

# ---- 建立 hermes 指令捷徑 ----
LINK_TARGET="$HOME/.local/bin/hermes"
install -d "$HOME/.local/bin"
if [ -f "$REPO_DIR/cli.py" ]; then
  printf '#!/bin/bash\nsource "%s/bin/activate"\npython "%s/cli.py" "$@"\n' \
    "$VENV_DIR" "$REPO_DIR" > "$LINK_TARGET"
  chmod +x "$LINK_TARGET"
  echo "==> 'hermes' 指令已安裝到 $LINK_TARGET"
else
  echo "警告：找不到 cli.py，跳過 hermes 指令建立"
fi

echo ""
echo "==> 修復 plugins.browser import 問題（Pi2 不需要雲端瀏覽器）"
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
    print("browser_tool.py 已修復")
PYEOF
fi

echo ""
echo "==> 完成！執行 'source ~/.bashrc && hermes' 開始使用"
