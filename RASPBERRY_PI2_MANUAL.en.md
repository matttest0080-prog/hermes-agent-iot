# Hermes Agent IoT: Raspberry Pi 2 / ARMv7 Operating Manual

This manual applies to the latest upstream-synced branch of `matttest0080-prog/hermes-agent-iot`. The Pi2 is the minimum baseline; the same profiles also work on Pi 3/4/5, Pi Zero 2 W, ARM64 SBCs, x86 mini PCs, and VMs.

## 1. Design Principles

The Pi2 handles only a lightweight Agent, MQTT, Home Assistant, Session/FTS memory, and remote API coordination. The following work should stay on stronger LAN/Cloud nodes:

- Large LLM inference
- Embedding models
- `torch` / `sentence-transformers`
- Chroma, Qdrant, or pgvector
- Image / video generation
- Chromium / Computer Use

Recommended topology:

```text
Pi2 Hermes Agent -> MQTT/HTTP -> MCU, sensors, Home Assistant
       |
       +---------- HTTPS/LAN -> remote LLM
       +---------- HTTPS/LAN -> central RAG/Honcho/FTS5 API
```

Hard real-time control, motor protection, obstacle-avoidance reflex, and emergency stop must stay on the MCU/PLC/ROS controller — they must not be delegated to an LLM.

## 2. System Requirements

- Python `>=3.11,<3.14`
- Git
- Python venv
- About 1 GB RAM; enabling swap for installation is recommended
- A remote or LAN OpenAI-compatible model endpoint

If Raspberry Pi OS is still on Python 3.9, install Python 3.11+ first.

## 3. Installation

### 3.1 Public PyPI wheel (0.21.0.post1 published; not yet verified on physical Pi2)

The currently published version is `hermes-agent-iot 0.21.0.post1`. The last physical Pi2 verification remains `0.20.6.post1`: clean-installed from public PyPI onto a physical Raspberry Pi 2 Model B Rev 1.1 (`armv7l`, 32-bit, 921 MiB RAM, Python 3.13.5), passing the `minimal` profile, CLI, `pip check`, and permission smoke tests.

You must use a virtualenv with Python `>=3.11,<3.14`; do not use system pip, `sudo pip`, or `--break-system-packages`:

```bash
python3 --version
python3 -m venv ~/.venvs/hermes-iot
source ~/.venvs/hermes-iot/bin/activate

python -m pip install --upgrade pip
python -m pip install 'hermes-agent-iot[minimal]==0.21.0.post1'
python -m pip check

hermes-iot setup --profile minimal
hermes-iot profile show
command -v hermes
command -v hermes-iot
hermes setup model
hermes
```

Do not install the upstream `hermes-agent` distribution into the same virtualenv; the two distributions ship overlapping Python modules and CLIs. `hermes-iot setup` will not overwrite an existing `~/.hermes/config.yaml`.

Supply-chain identifiers:

```text
PyPI:       https://pypi.org/project/hermes-agent-iot/0.21.0.post1/
Tag:        iot-v0.21.0.post1
Commit:     55a478a4eab64672222578d3f58086055fc911a4
Wheel:      hermes_agent_iot-0.21.0.post1-py3-none-any.whl
SHA-256:    83659f6b23a369f95c4b977257d54ba8f342c10155e4ce71675f059f3fd1f023
Workflow:   https://github.com/matttest0080-prog/hermes-agent-iot/actions/runs/33470551659
```

This release publishes a single universal wheel and no sdist; public PyPI provenance is bound to repository `matttest0080-prog/hermes-agent-iot`, workflow `publish-pypi.yml`, and the protected `pypi` Environment.

### 3.2 `pi2-lite` source installation

Use this path when you need the full in-repository skills/catalog, locale files, Dashboard/TUI assets, or source development files:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip build-essential

git clone --branch pi2-lite --depth 1 \
  https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
```

Use the single maintained installer:

```bash
bash setup-pi2-minimal.sh --profile minimal
```

`setup-pi2.sh` is only a backward-compatibility wrapper that forwards to `setup-pi2-minimal.sh`; it no longer maintains a second dependency list.

### Profiles

```text
minimal  CLI + PTY, lowest resource usage
iot      minimal + MCP/ACP/Home Assistant/MQTT/SMS
rag      iot + Honcho; central/remote RAG preferred
full     for stronger ARM64/x86 hosts
dev      full + test and development dependencies
```

Examples:

```bash
bash setup-pi2-minimal.sh --profile iot
bash setup-pi2-minimal.sh --profile rag
```

The installer:

- Validates Python 3.11–3.13
- Creates `~/.hermes-venv`
- Uses `pyproject.toml` as the single dependency source via `pip install -e '.[extras]'`
- Does not install a separate unpinned package list
- Does not preinstall torch, Chroma, or a local embedding stack on the Pi2
- Creates `~/.hermes/config.yaml` only when no config exists yet

Startup:

```bash
source ~/.hermes-venv/bin/activate
hermes --help
hermes setup model
hermes
```

## 4. Pi2 Config Templates

```text
templates/config.pi2-core.yaml
templates/config.pi2-native.yaml
templates/config.pi2-rag.yaml
```

The current config schema uses:

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

Prefer writing the model/provider with `hermes setup model`; do not hand-create legacy `models:` lists, list-typed `providers:`, or `tools:` keys.

API keys belong in `~/.hermes/.env`; behavioral settings belong in `config.yaml`.

## 5. Context Floor

Official Hermes maintains a roughly 64K tooling-workflow floor by default. The Pi2 profiles deliberately lower it to:

```text
core:   2,048
native: 8,192
rag:    8,192
```

This is a low-resource degradation mode; it does not mean the full tool schema runs reliably within 2K. 2K should only be paired with a very small tool surface; for coding, multi-tool use, long conversations, and RAG, use a remote 64K+ model.

## 6. MQTT

MQTT is an independent, explicitly opt-in toolset; it is not automatically added to every CLI, Gateway, or Cron session just because `MQTT_HOST` is present in the environment.

Enable it:

```bash
source ~/.hermes-venv/bin/activate
hermes tools enable mqtt
```

Configure secrets and connection info:

```bash
export MQTT_HOST=192.168.1.10
export MQTT_PORT=1883
export MQTT_USERNAME=iot-user
export MQTT_PASSWORD='replace-me'
export MQTT_CLIENT_ID=pi2-edge  # optional prefix; Hermes appends a unique suffix
export MQTT_TLS=true
```

Tools:

- `mqtt_publish`
- `mqtt_subscribe_recent`
- `mqtt_device_command`

Security recommendations:

- Use TLS for the broker
- Use a separate account per Hermes node
- Broker ACL allows only the designated topic prefix
- Sensor accounts are read-only by default
- Actuator command topics require separate authorization
- Emergency stop and hardware safety must not depend on MQTT/LLM
- Avoid enabling the MQTT toolset on public Gateway sessions that do not need device control
- When setting an account or password without TLS, it fails closed; only an isolated, trusted plaintext lab network should explicitly set `MQTT_ALLOW_INSECURE_CREDENTIALS=true`
- Setting `MQTT_PASSWORD` alone without `MQTT_USERNAME` fails closed
- `MQTT_CLIENT_ID` is a prefix, not a fixed ID; Hermes appends a process/random suffix to avoid concurrent tool calls kicking each other offline
- Inbound payloads are limited to 64 KiB per message before UTF-8 decoding, and at most 256 KiB cumulative per subscription or command/ACK response; oversized messages are dropped and reported in the response

`mqtt_device_command` completes the state/ACK subscription before publishing the command, so an immediate ACK is not lost before the subscription is established.

## 7. Central RAG

The Pi2 RAG profile uses:

- Hermes built-in memory
- Session Search
- SQLite/FTS5
- Honcho (optional)
- Remote embedding / central vector store

Do not mount a single writable SQLite DB over NFS/Samba to multiple Pi2s. Write to a central service over an HTTP API, or use a local DB per device and sync afterwards.

Recommended metadata:

```json
{
  "device_id": "pi2-lab",
  "scope": "global|device|room|user",
  "source": "conversation|sensor|manual",
  "created_at": "ISO-8601 timestamp"
}
```

## 8. llama.cpp (Pi2B-specific workflow)

Running a 7B model locally on the Pi2 is generally impractical; run large models on a LAN host first. To use a small local GGUF on the Raspberry Pi 2B, use the `pi2b-armv7` branch maintained by this project — do not treat `ggml-org/llama.cpp` `master` as the Pi2 version.

```text
Pi2 branch:
https://github.com/matttest0080-prog/llama.cpp/tree/pi2b-armv7

Upstream master:
https://github.com/ggml-org/llama.cpp
```

### 8.1 Get the correct Pi2 branch

If not yet downloaded:

```bash
git clone --branch pi2b-armv7 --depth 1 \
  https://github.com/matttest0080-prog/llama.cpp.git \
  "$HOME/llama.cpp"
cd "$HOME/llama.cpp"
```

If your existing `~/llama.cpp` came from `ggml-org/llama.cpp`, do not just run `git pull` to update upstream `master`. Add the Pi2 fork and switch branch:

```bash
cd "$HOME/llama.cpp"

git remote get-url pi2 >/dev/null 2>&1 || \
  git remote add pi2 https://github.com/matttest0080-prog/llama.cpp.git

git fetch pi2 pi2b-armv7
```

If the local Pi2 branch does not exist yet:

```bash
git switch --track -c pi2b-armv7 pi2/pi2b-armv7
```

If the local Pi2 branch already exists:

```bash
git switch pi2b-armv7
git pull --ff-only pi2 pi2b-armv7
```

Verify:

```bash
git branch --show-current
uname -m
ls -l scripts/build-pi2-armv7.sh
```

Expected:

```text
pi2b-armv7
armv7l
scripts/build-pi2-armv7.sh exists
```

### 8.2 Install build dependencies

```bash
sudo apt update
sudo apt install -y cmake build-essential pkg-config git python3-full python3-venv

cmake --version
gcc --version
g++ --version
```

The Pi2 has only about 1 GB RAM. Check before compiling:

```bash
free -h
swapon --show
```

If there is no swap, you can temporarily create a 1 GB swap for the build. Swap is not normal inference memory and increases SD card writes:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
free -h
```

### 8.3 Build the Pi2 llama-server

```bash
cd "$HOME/llama.cpp"
./scripts/build-pi2-armv7.sh
```

This script uses:

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

After the build, the binary is at:

```text
$HOME/llama.cpp/build-pi2-armv7/bin/llama-server
```

Verify:

```bash
ls -lh "$HOME/llama.cpp/build-pi2-armv7/bin/llama-server"
"$HOME/llama.cpp/build-pi2-armv7/bin/llama-server" --version
```

Note: if you are currently in `$HOME`, you cannot use:

```bash
./build-pi2-armv7/bin/llama-server
```

because the correct path is under `$HOME/llama.cpp`. `cd "$HOME/llama.cpp"` first, or use the full path.

### 8.4 Install the Hugging Face CLI (avoiding PEP 668)

Raspberry Pi OS system Python is protected by PEP 668. Do not run directly:

```bash
python -m pip install ...
```

And do not use:

```bash
--break-system-packages
```

Create an isolated virtualenv:

```bash
python3 -m venv "$HOME/.venvs/huggingface"
"$HOME/.venvs/huggingface/bin/python" -m pip install --upgrade pip
"$HOME/.venvs/huggingface/bin/python" -m pip install 'huggingface-hub[cli]'

export PATH="$HOME/.venvs/huggingface/bin:$PATH"
echo 'export PATH="$HOME/.venvs/huggingface/bin:$PATH"' >> "$HOME/.bashrc"

hf --version
```

### 8.5 Download a Pi2-suitable Gemma GGUF

The following repository has been confirmed to contain `Q4_K_M` files:

```text
lmstudio-community/gemma-3-270m-it-GGUF
```

Download:

```bash
mkdir -p "$HOME/models"

hf download lmstudio-community/gemma-3-270m-it-GGUF \
  gemma-3-270m-it-Q4_K_M.gguf \
  --local-dir "$HOME/models"
```

Verify:

```bash
ls -lh "$HOME/models/gemma-3-270m-it-Q4_K_M.gguf"
```

Confirmed filename:

```text
gemma-3-270m-it-Q4_K_M.gguf
```

Do not treat the placeholder in the following command as the actual filename:

```bash
hf download OWNER/MODEL-GGUF model.gguf --local-dir "$HOME/models"
```

`ggml-org/gemma-3-270m-it-GGUF` currently only has `Q8_0`, not `Q4_K_M`. If you use that repository, the command must be:

```bash
hf download ggml-org/gemma-3-270m-it-GGUF \
  gemma-3-270m-it-Q8_0.gguf \
  --local-dir "$HOME/models"
```

### 8.6 Start and verify

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

Check the model endpoint:

```bash
curl -fsS http://127.0.0.1:8080/v1/models
```

Check the chat endpoint:

```bash
curl -fsS http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "pi2-local",
    "messages": [{"role": "user", "content": "Reply with exactly OK"}],
    "max_tokens": 4
  }'
```

### 8.7 Hermes fallback configuration

After starting llama-server, run:

```bash
source ~/.hermes-venv/bin/activate
hermes setup model
```

Select:

```text
Local AI (llama.cpp / llama-server)
```

Confirm the settings:

```text
Base URL: http://127.0.0.1:8080/v1
API key:  local
Model:    pi2-local
```

The Pi2 profile's `fallback_providers` already pre-configures a local `custom` endpoint. Normally Hermes uses the remote model; it only switches to the local llama-server on remote connection errors, 5xx, authentication failures, rate limits, or billing-type errors.

The local endpoint listens only on `127.0.0.1` and is not exposed to the LAN directly. To open it to the LAN, you must separately configure authentication, ACLs, and a firewall — never expose an unauthenticated inference endpoint directly.

Note: the llama.cpp server source currently still has `mtmd` and `llama-ui` target dependencies; `LLAMA_BUILD_UI=OFF` avoids embedding UI assets but does not remove all related source. This Pi2 branch deliberately avoids an invasive multimodal API refactor.

Do not use `-DLLAMA_CURL=OFF` as a control knob anymore; upstream CMake has marked `LLAMA_CURL` as deprecated. The Hub download feature is not needed when using a local GGUF.

After the build, if swap was enabled only for the build, you can turn it off and delete it:

```bash
sudo swapoff /swapfile
sudo rm -f /swapfile
```

## 9. Verification & Maintenance

```bash
source ~/.hermes-venv/bin/activate
hermes --help
hermes tools list
python scripts/check_pi2_install_guards.py --repo .
```

Check for updates:

```bash
git fetch upstream main
git log --oneline HEAD..upstream/main
```

After every upstream sync, run at least:

```bash
pytest -q tests/test_mqtt_tool.py tests/test_pi2_install_guards.py
uv lock --check
ruff check tools/mqtt_tool.py agent/agent_init.py agent/conversation_loop.py
```

## 10. Troubleshooting

Out of memory:

```bash
free -h
swapon --show
```

MQTT not working:

```bash
python -c 'import paho.mqtt.client; print("paho-mqtt ok")'
printenv MQTT_HOST
hermes tools list
```

When the model context is rejected, confirm the two values match:

```yaml
model:
  context_length: 8192
agent:
  minimum_tool_context_length: 8192
```

If the profile has already lowered the context floor but the tool schema is still too large, disable more toolsets or use a remote 64K+ model instead of lowering the floor further.
