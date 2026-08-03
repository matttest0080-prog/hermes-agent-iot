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
IoT      minimal + MCP/ACP/Home Assistant/MQTT/SMS
rag      IoT + Honcho；中央／遠端 RAG 優先
full     較強 ARM64/x86 主機使用
Dev      full + 測試與開發依賴
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

## 8. llama.cpp（進階）

Pi2 本機執行 7B 模型通常不實用；優先在 LAN 主機執行 `llama-server`。若仍要在 ARM 裝置編譯，使用 llama.cpp 現行 CMake 介面：

```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_NATIVE=OFF
cmake --build build --config Release -j2 --target llama-server
```

下載 GGUF 可使用新版 Hugging Face CLI：

```bash
python -m pip install 'huggingface-hub[cli]'
hf download OWNER/MODEL-GGUF model.gguf --local-dir ~/models
```

啟動現行 server binary：

```bash
./build/bin/llama-server \
  -m ~/models/model.gguf \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 8192
```

檢查：

```bash
curl http://127.0.0.1:8080/v1/models
```

然後執行：

```bash
hermes setup model
```

選擇 Custom／OpenAI-compatible endpoint，Base URL 設為：

```text
http://127.0.0.1:8080/v1
```

使用互動設定：

```bash
hermes setup model
# 選擇：Local AI (llama.cpp / llama-server)
```

此選項預填 `http://127.0.0.1:8080/v1`、`local` 與 `pi2-local`，並會嘗試從 `/v1/models` 自動讀取模型清單。

Pi2 profile 的 `fallback_providers` 已預設加入本機 `custom` endpoint。遠端模型仍放在 `model:`，因此正常情況使用遠端；只有遠端發生連線錯誤、5xx、認證失敗、rate limit 或 billing 類錯誤時，Hermes 才切換到本機 llama-server。

llama-server 必須使用與 template 相同的 model alias：

```bash
./build/bin/llama-server \
  -m ~/models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --alias pi2-local \
  --host 127.0.0.1 \
  --port 8080 \
  --ctx-size 2048 \
  --parallel 1
```

確認本機 fallback endpoint：

```bash
curl -fsS http://127.0.0.1:8080/v1/models
```

`fallback_providers` 的本機 endpoint 只監聽 `127.0.0.1`，不會直接暴露到 LAN。Pi2 core/native/rag profile 使用較低的 context floor；本機小模型只應處理簡短對話和簡單 IoT 指令，複雜工具工作仍應交給遠端模型。

如果本機 llama-server 沒有啟動，Hermes 會記錄 fallback 失敗並回報遠端與本機都不可用，不會假裝已完成工作。

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
