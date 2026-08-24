# Hermes Agent IoT：Raspberry Pi 2／ARMv7 操作手冊

本手冊適用於 `matttest0080-prog/hermes-agent-iot` 的最新 upstream 同步分支。Pi2 是最低基準；相同 Profile 也可用於 Pi 3/4/5、Pi Zero 2 W、ARM64 SBC、x86 小主機與 VM。

## 1. 設計原則

Pi2 僅負責輕量 Agent、MQTT、Home Assistant、Session/FTS 記憶和遠端 API 協調。以下工作應放在較強的 LAN／Cloud 節點：

- 大型 LLM 推論
- Embedding 模型
- `torch`／`sentence-transformers`
- Chroma、Qdrant 或 pgvector
- 影像／影片生成
- Chromium／Computer Use

推薦拓撲：

```text
Pi2 Hermes Agent -> MQTT/HTTP -> MCU、感測器、Home Assistant
       |
       +---------- HTTPS/LAN -> 遠端 LLM
       +---------- HTTPS/LAN -> 中央 RAG／Honcho／FTS5 API
```

硬即時控制、馬達保護、障礙反射與緊急停止必須留在 MCU／PLC／ROS controller，不能交由 LLM。

## 2. 系統需求

- Python `>=3.11,<3.14`
- Git
- Python venv
- 約 1 GB RAM；建議啟用 swap 供安裝使用
- 遠端或 LAN OpenAI-compatible model endpoint

Raspberry Pi OS 若仍是 Python 3.9，必須先安裝 Python 3.11+。

## 3. 安裝

### 3.1 公開 PyPI wheel（已完成實體 Pi2 驗證）

目前已驗證版本是 `hermes-agent-iot 0.20.5.post2`。它已從公開 PyPI
clean-install 到實體 Raspberry Pi 2 Model B Rev 1.1（`armv7l`、32-bit、
921 MiB RAM、Python 3.13.5），並通過 `minimal` Profile、CLI、`pip check`
與權限 smoke test。

必須使用 Python `>=3.11,<3.14` 的 virtualenv；不要使用 system pip、
`sudo pip` 或 `--break-system-packages`：

```bash
python3 --version
python3 -m venv ~/.venvs/hermes-iot
source ~/.venvs/hermes-iot/bin/activate

python -m pip install --upgrade pip
python -m pip install 'hermes-agent-iot[minimal]==0.20.5.post2'
python -m pip check

hermes-iot setup --profile minimal
hermes-iot profile show
command -v hermes
command -v hermes-iot
hermes setup model
hermes
```

不要將上游 `hermes-agent` distribution 安裝到同一個 virtualenv；兩個
distribution 會提供重疊的 Python modules 與 CLI。`hermes-iot setup` 不會
覆寫既有的 `~/.hermes/config.yaml`。

供應鏈識別：

```text
PyPI:       https://pypi.org/project/hermes-agent-iot/0.20.5.post2/
Tag:        iot-v0.20.5.post2
Commit:     b20d9eac292f6eab76c725cfe0bf46fde7f67425
Wheel:      hermes_agent_iot-0.20.5.post2-py3-none-any.whl
SHA-256:    2de6f2615f53e51cf7c90b05c564e027439946f3eec069780cd0404017814629
Workflow:   https://github.com/matttest0080-prog/hermes-agent-iot/actions/runs/32724087830
```

此版本只發布一個 universal wheel，沒有 sdist；公開 PyPI provenance 綁定
repository `matttest0080-prog/hermes-agent-iot`、workflow
`publish-pypi.yml` 與受保護的 `pypi` Environment。

### 3.2 `pi2-lite` 原始碼安裝

若需要 repository 內完整 skills／catalog、語系檔、Dashboard/TUI 資產或
source development 檔案，請使用此路徑：

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip build-essential

git clone --branch pi2-lite --depth 1 \
  https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
```

使用唯一維護的安裝器：

```bash
bash setup-pi2-minimal.sh --profile minimal
```

`setup-pi2.sh` 僅是向後相容 wrapper，會直接轉交給 `setup-pi2-minimal.sh`；它不再維護第二套依賴清單。

### Profiles

```text
minimal  CLI + PTY，最低資源
iot      minimal + MCP/ACP/Home Assistant/MQTT/SMS
rag      iot + Honcho；中央／遠端 RAG 優先
full     較強 ARM64/x86 主機使用
dev      full + 測試與開發依賴
```

範例：

```bash
bash setup-pi2-minimal.sh --profile iot
bash setup-pi2-minimal.sh --profile rag
```

安裝器：

- 驗證 Python 3.11–3.13
- 建立 `~/.hermes-venv`
- 以 `pip install -e '.[extras]'` 使用 `pyproject.toml` 作為唯一依賴來源
- 不另外安裝未鎖定的套件清單
- 不在 Pi2 預裝 torch、Chroma 或本機 embedding stack
- 只在尚無設定時建立 `~/.hermes/config.yaml`

啟動：

```bash
source ~/.hermes-venv/bin/activate
hermes --help
hermes setup model
hermes
```

## 4. Pi2 設定模板

```text
templates/config.pi2-core.yaml
templates/config.pi2-native.yaml
templates/config.pi2-rag.yaml
```

目前 config schema 使用：

```yaml
model: ""
providers: {}
fallback_providers:
  # Remote primary is configured in model:. When it fails, Hermes uses
  # the local llama-server endpoint below.
  - provider: custom
    model: pi2-local
    base_url: http://127.0.0.1:8080/v1
    api_key: local

platform_toolsets:
  cli:
    - hermes-cli
    - mqtt

agent:
  api_max_retries: 0
  minimum_tool_context_length: 2048  # core; native/rag use 8192

memory:
  memory_enabled: true
  user_profile_enabled: true
  provider: ""
```

推薦使用 `hermes setup model` 寫入 Model／Provider，不要手工建立舊版 `models:` list、list 型 `providers:` 或 `tools:` keys。

API key 應放在 `~/.hermes/.env`，行為設定放在 `config.yaml`。

## 5. Context Floor

官方 Hermes 預設維持約 64K 工具工作流門檻。Pi2 Profile 明確降低為：

```text
core:   2,048
native: 8,192
rag:    8,192
```

這是低資源降級模式，不代表完整工具 schema 能在 2K 內可靠運行。2K 只應搭配極小工具面；Coding、多工具、長對話與 RAG 建議使用遠端 64K+ 模型。

## 6. MQTT

MQTT 是獨立、明確 opt-in toolset，不會只因系統存在 `MQTT_HOST` 就自動加入所有 CLI、Gateway 或 Cron Session。

啟用：

```bash
source ~/.hermes-venv/bin/activate
hermes tools enable mqtt
```

設定秘密與連線資訊：

```bash
export MQTT_HOST=192.168.1.10
export MQTT_PORT=1883
export MQTT_USERNAME=iot-user
export MQTT_PASSWORD='replace-me'
export MQTT_CLIENT_ID=pi2-edge  # 選填 prefix；Hermes 會附加唯一 suffix
export MQTT_TLS=true
```

工具：

- `mqtt_publish`
- `mqtt_subscribe_recent`
- `mqtt_device_command`

安全建議：

- Broker 使用 TLS
- 每個 Hermes node 使用獨立帳號
- Broker ACL 僅允許指定 topic prefix
- 感測器帳號預設只讀
- Actuator command topic 另外授權
- 緊急停止與硬安全不得依賴 MQTT／LLM
- 避免將 MQTT toolset 啟用於不需要裝置控制的公開 Gateway Session
- 設定帳號或密碼時，未啟用 TLS 會 fail closed；只有隔離且可信任的明文實驗網路才應明確設定 `MQTT_ALLOW_INSECURE_CREDENTIALS=true`
- 單獨設定 `MQTT_PASSWORD` 而未設定 `MQTT_USERNAME` 會 fail closed
- `MQTT_CLIENT_ID` 是 prefix，不是固定 ID；Hermes 會附加 process/random suffix，避免並行 tool call 互相踢線
- 入站 payload 會在 UTF-8 解碼前限制為單條 64 KiB，且每次訂閱或 command/ACK 回應累計最多 256 KiB；超限訊息會丟棄並在回應中報告

`mqtt_device_command` 會先完成 state/ACK 訂閱，再發布命令，以避免立即 ACK 在訂閱建立前遺失。

## 7. 中央 RAG

Pi2 RAG Profile 使用：

- Hermes built-in memory
- Session Search
- SQLite／FTS5
- Honcho（可選）
- 遠端 embedding／中央向量庫

不要把一個可寫 SQLite DB 直接掛載到多台 Pi2 的 NFS／Samba。應透過 HTTP API 寫入中央服務，或每台裝置使用本機 DB 後再同步。

推薦 metadata：

```json
{
  "device_id": "pi2-lab",
  "scope": "global|device|room|user",
  "source": "conversation|sensor|manual",
  "created_at": "ISO-8601 timestamp"
}
```

## 8. llama.cpp（Pi2B 專用流程）

Pi2 本機執行 7B 模型通常不實用；優先在 LAN 主機執行大型模型。若要在 Raspberry Pi 2B 使用小型本機 GGUF，請使用本專案維護的 `pi2b-armv7` branch，不要直接把 `ggml-org/llama.cpp` 的 `master` 當成 Pi2 版本。

```text
Pi2 branch:
https://github.com/matttest0080-prog/llama.cpp/tree/pi2b-armv7

Upstream master:
https://github.com/ggml-org/llama.cpp
```

### 8.1 取得正確的 Pi2 branch

如果尚未下載：

```bash
git clone --branch pi2b-armv7 --depth 1 \
  https://github.com/matttest0080-prog/llama.cpp.git \
  "$HOME/llama.cpp"
cd "$HOME/llama.cpp"
```

如果現有 `~/llama.cpp` 是從 `ggml-org/llama.cpp` 下載的，請不要直接執行 `git pull` 更新 upstream `master`。加入 Pi2 fork 並切換 branch：

```bash
cd "$HOME/llama.cpp"

git remote get-url pi2 >/dev/null 2>&1 || \
  git remote add pi2 https://github.com/matttest0080-prog/llama.cpp.git

git fetch pi2 pi2b-armv7
```

如果本機還沒有 Pi2 branch：

```bash
git switch --track -c pi2b-armv7 pi2/pi2b-armv7
```

如果本機已經有 Pi2 branch：

```bash
git switch pi2b-armv7
git pull --ff-only pi2 pi2b-armv7
```

確認：

```bash
git branch --show-current
uname -m
ls -l scripts/build-pi2-armv7.sh
```

預期：

```text
pi2b-armv7
armv7l
scripts/build-pi2-armv7.sh 存在
```

### 8.2 安裝 build 依賴

```bash
sudo apt update
sudo apt install -y cmake build-essential pkg-config git python3-full python3-venv

cmake --version
gcc --version
g++ --version
```

Pi2 只有約 1 GB RAM。編譯前檢查：

```bash
free -h
swapon --show
```

如果沒有 swap，可暫時建立 1 GB swap 供編譯使用。swap 不是正常推理記憶體，且會增加 SD 卡寫入：

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
free -h
```

### 8.3 編譯 Pi2 llama-server

```bash
cd "$HOME/llama.cpp"
./scripts/build-pi2-armv7.sh
```

此 script 會使用：

```text
GGML_NATIVE=OFF
GGML_OPENMP=OFF
CPU-only
LLAMA_BUILD_TESTS=OFF
LLAMA_BUILD_EXAMPLES=OFF
LLAMA_BUILD_APP=OFF
LLAMA_BUILD_UI=OFF
-j1
```

編譯完成後，binary 位於：

```text
$HOME/llama.cpp/build-pi2-armv7/bin/llama-server
```

確認：

```bash
ls -lh "$HOME/llama.cpp/build-pi2-armv7/bin/llama-server"
"$HOME/llama.cpp/build-pi2-armv7/bin/llama-server" --version
```

注意：如果你目前在 `$HOME`，不能使用：

```bash
./build-pi2-armv7/bin/llama-server
```

因為正確路徑是在 `$HOME/llama.cpp` 裡。請先 `cd "$HOME/llama.cpp"`，或直接使用完整路徑。

### 8.4 安裝 Hugging Face CLI（避免 PEP 668）

Raspberry Pi OS 的系統 Python 受到 PEP 668 保護。不要直接執行：

```bash
python -m pip install ...
```

也不要使用：

```bash
--break-system-packages
```

建立獨立 virtualenv：

```bash
python3 -m venv "$HOME/.venvs/huggingface"
"$HOME/.venvs/huggingface/bin/python" -m pip install --upgrade pip
"$HOME/.venvs/huggingface/bin/python" -m pip install 'huggingface-hub[cli]'

export PATH="$HOME/.venvs/huggingface/bin:$PATH"
echo 'export PATH="$HOME/.venvs/huggingface/bin:$PATH"' >> "$HOME/.bashrc"

hf --version
```

### 8.5 下載適合 Pi2 的 Gemma GGUF

以下 repository 已確認包含 `Q4_K_M` 檔案：

```text
lmstudio-community/gemma-3-270m-it-GGUF
```

下載：

```bash
mkdir -p "$HOME/models"

hf download lmstudio-community/gemma-3-270m-it-GGUF \
  gemma-3-270m-it-Q4_K_M.gguf \
  --local-dir "$HOME/models"
```

確認：

```bash
ls -lh "$HOME/models/gemma-3-270m-it-Q4_K_M.gguf"
```

已確認的檔名：

```text
gemma-3-270m-it-Q4_K_M.gguf
```

不要把下列命令中的 placeholder 當作實際檔案名稱：

```bash
hf download OWNER/MODEL-GGUF model.gguf --local-dir "$HOME/models"
```

`ggml-org/gemma-3-270m-it-GGUF` 目前只有 `Q8_0`，沒有 `Q4_K_M`。如果要使用該 repository，命令必須是：

```bash
hf download ggml-org/gemma-3-270m-it-GGUF \
  gemma-3-270m-it-Q8_0.gguf \
  --local-dir "$HOME/models"
```

### 8.6 啟動與驗證

```bash
"$HOME/llama.cpp/build-pi2-armv7/bin/llama-server" \
  -m "$HOME/models/gemma-3-270m-it-Q4_K_M.gguf" \
  --alias pi2-local \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 2048 \
  --parallel 1 \
  --threads 4 \
  -ngl 0
```

檢查 model endpoint：

```bash
curl -fsS http://127.0.0.1:8080/v1/models
```

檢查 chat endpoint：

```bash
curl -fsS http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "pi2-local",
    "messages": [{"role": "user", "content": "Reply with exactly OK"}],
    "max_tokens": 4
  }'
```

### 8.7 Hermes fallback 設定

啟動 llama-server 後執行：

```bash
source ~/.hermes-venv/bin/activate
hermes setup model
```

選擇：

```text
Local AI (llama.cpp / llama-server)
```

確認設定：

```text
Base URL: http://127.0.0.1:8080/v1
API key:  local
Model:    pi2-local
```

Pi2 profile 的 `fallback_providers` 已預設加入本機 `custom` endpoint。正常情況使用遠端模型；只有遠端連線錯誤、5xx、認證失敗、rate limit 或 billing 類錯誤時，Hermes 才切換到本機 llama-server。

本機 endpoint 只監聽 `127.0.0.1`，不會直接暴露到 LAN。若要開放 LAN，必須另外設定驗證、ACL 與防火牆，不能直接暴露未授權的 inference endpoint。

注意：目前 llama.cpp 的 server source 仍有 `mtmd` 與 `llama-ui` target dependency；`LLAMA_BUILD_UI=OFF` 會避免嵌入 UI assets，但不會移除所有相關 source。此 Pi2 branch 刻意不做侵入式 multimodal API refactor。

不要再使用 `-DLLAMA_CURL=OFF` 作為目前的控制項；upstream CMake 已將 `LLAMA_CURL` 標記為 deprecated。使用本機 GGUF 時不需要 Hub download 功能。

完成編譯後，如果 swap 只為了建置而啟用，可以關閉並刪除：

```bash
sudo swapoff /swapfile
sudo rm -f /swapfile
```

## 10. 驗證與維護

```bash
source ~/.hermes-venv/bin/activate
hermes --help
hermes tools list
python scripts/check_pi2_install_guards.py --repo .
```

檢查更新：

```bash
git fetch upstream main
git log --oneline HEAD..upstream/main
```

每次同步 upstream 後至少執行：

```bash
pytest -q tests/test_mqtt_tool.py tests/test_pi2_install_guards.py
uv lock --check
ruff check tools/mqtt_tool.py agent/agent_init.py agent/conversation_loop.py
```

## 10. 故障排除

記憶體不足：

```bash
free -h
swapon --show
```

MQTT 無法使用：

```bash
python -c 'import paho.mqtt.client; print("paho-mqtt ok")'
printenv MQTT_HOST
hermes tools list
```

Model context 被拒絕時，確認兩者一致：

```yaml
model:
  context_length: 8192
agent:
  minimum_tool_context_length: 8192
```

若 Profile 已降低 context floor 但工具 schema 仍過大，應關閉更多 toolsets 或改用遠端 64K+ 模型，而不是繼續降低門檻。
