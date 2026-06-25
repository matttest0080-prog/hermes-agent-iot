#!/bin/bash
# ============================================================
# fix-browser-import.sh
# Fix the "No module named 'plugins.browser'" error on Pi2
# Run from the hermes-agent-iot directory: bash fix-browser-import.sh
# ============================================================

set -e

BROWSER_TOOL="tools/browser_tool.py"

if [ ! -f "$BROWSER_TOOL" ]; then
  echo "Error: $BROWSER_TOOL not found; run this script from the repo root"
  exit 1
fi

echo "==> Backing up the original file"
cp "$BROWSER_TOOL" "${BROWSER_TOOL}.bak"

echo "==> Replacing hard plugins.browser imports with try/except"

python3 - <<'PYEOF'
import re

with open("tools/browser_tool.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the three plugins.browser imports with try/except versions
old = '''from plugins.browser.browserbase.provider import (
    BrowserbaseBrowserProvider as BrowserbaseProvider,
)
from plugins.browser.browser_use.provider import (
    BrowserUseBrowserProvider as BrowserUseProvider,
)
from plugins.browser.firecrawl.provider import (
    FirecrawlBrowserProvider as FirecrawlProvider,
)'''

new = '''try:
    from plugins.browser.browserbase.provider import (
        BrowserbaseBrowserProvider as BrowserbaseProvider,
    )
except ImportError:
    BrowserbaseProvider = None  # not available on this platform

try:
    from plugins.browser.browser_use.provider import (
        BrowserUseBrowserProvider as BrowserUseProvider,
    )
except ImportError:
    BrowserUseProvider = None  # not available on this platform

try:
    from plugins.browser.firecrawl.provider import (
        FirecrawlBrowserProvider as FirecrawlProvider,
    )
except ImportError:
    FirecrawlProvider = None  # not available on this platform'''

if old in content:
    content = content.replace(old, new)
    with open("tools/browser_tool.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("==> Updated successfully")
else:
    print("Warning: expected import block not found; this version may differ")
    print("Please manually wrap the following imports in try/except:")
    print("  from plugins.browser.browserbase.provider import ...")
    print("  from plugins.browser.browser_use.provider import ...")
    print("  from plugins.browser.firecrawl.provider import ...")
PYEOF

echo ""
echo "==> Done! Restart the agent to apply the change"
echo "    To restore: cp ${BROWSER_TOOL}.bak $BROWSER_TOOL"
