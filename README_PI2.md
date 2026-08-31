# Hermes Agent IoT / Raspberry Pi 2+ profile

This repository is a Pi2/IoT-oriented flavor of the upstream Hermes Agent source:

- Upstream: `https://github.com/NousResearch/hermes-agent`
- IoT fork: `https://github.com/matttest0080-prog/hermes-agent-iot`

Goal: preserve native Hermes Agent architecture and feature compatibility while making the default Raspberry Pi 2 install small enough to be practical on ARMv7 / 1GB RAM.

This profile is primarily designed for embedded-system development: always-on controllers, sensor/automation nodes, lab devices, robotics gateways, home/industrial IoT boxes, and other constrained Linux deployments where low memory use, predictable dependencies, and remote-first AI services matter more than desktop-heavy local stacks.

Raspberry Pi 2 is the minimum/baseline target for this profile, not the maximum supported device. The same lightweight install path is suitable for Pi2-class or better Linux systems such as Raspberry Pi 3/4/5, Pi Zero 2 W, ARM64 SBCs, x86 mini PCs, and VMs. On stronger hardware, you can keep the safe Pi2 defaults or opt into heavier Hermes extras after install.

This is not a separate mini-agent. The Python package path, CLI entrypoint, tools, plugins, gateway, memory, cron, MCP, ACP, and provider architecture stay intact. The Pi2 profile only changes default installation choices and default enabled tool surface.

## What is preserved

Kept as native Hermes functionality:

- `hermes` CLI entrypoint from `pyproject.toml`
- core agent loop and provider routing
- tools system and toolsets
- skills system
- persistent memory and session search
- cron scheduler
- delegation/subagents
- MCP and ACP code paths
- gateway and platform adapters
- plugins and memory provider plugins
- OpenAI-compatible endpoints, including local `llama.cpp` servers

## What is slimmed

The Pi2 profile avoids eager install/use of heavy features:

- browser automation runtime
- local Chromium/Playwright-style stacks
- image/video generation backends
- voice/STT dependencies such as faster-whisper
- TTS premium providers
- torch / sentence-transformers / chromadb by default
- dashboard/web UI extras unless explicitly requested
- messaging platform extras unless explicitly requested

The code remains present. Heavy features can be re-enabled later with `hermes tools` and the relevant Python extras.

## Install profiles

Do not confuse these package **install profiles** with Hermes **instance
profiles** managed by `hermes profile`. The former pair a PyPI dependency extra
with a packaged default config; the latter isolate running Hermes instances.

PyPI users install exactly one public extra into a virtual environment, then
apply its config without invoking pip. Release `0.20.6.post1` is the current
published pin (`0.20.5.post2` remains the last physical-Pi2 baseline):

```bash
python3 --version  # must be >=3.11,<3.14
python3 -m venv ~/.venvs/hermes-iot
source ~/.venvs/hermes-iot/bin/activate

python -m pip install --upgrade pip
python -m pip install 'hermes-agent-iot[minimal]==0.20.6.post1'
hermes-iot setup --profile minimal
hermes-iot profile show
python -m pip check
command -v hermes
command -v hermes-iot
```

Do not use system pip, `sudo pip`, or `--break-system-packages`. Do not install
the upstream `hermes-agent` distribution into this virtual environment because
the two distributions provide overlapping Python modules and CLI commands.

The public extras aggregate the retained internal extras: `minimal=cli+pty`,
`iot=minimal+mcp+acp+homeassistant+mqtt+sms`, `rag=iot+honcho`, `full=all`, and
`dev=full+developer tools`. `full` and `dev` are not recommended on Pi2/1 GB.
If config already exists, setup leaves it untouched and prints the packaged
template path for comparison.

The PyPI wheel deliberately excludes repository-level bundled/optional skills,
optional MCP catalogs, and Desktop/TUI/Web build assets. Install from the
`pi2-lite` Git branch when those source-tree assets are needed. The `full` and
`dev` PyPI extras select broader Python dependencies; they are not Desktop
application bundles.

The wheel also excludes the repository's non-English locale catalog. It does
not silently download missing skills, MCP catalogs, locale files, Dashboard, or
TUI assets. Use the `pi2-lite` source installer for catalog browsing/install,
localized UI, Dashboard/TUI operation, or frontend/source development.

Release `0.20.6.post1` completed the x86_64 GitHub release gates and public
PyPI publish. Wheel SHA-256
`1393bfd72cc96f62965e4170f707911ee1b079ce12b45c4018043228b33f3197`
(commit `cb749957c66e537e951937f49251dbf18a4fb3c8`, workflow
https://github.com/matttest0080-prog/hermes-agent-iot/actions/runs/33358885842).
Last physical Raspberry Pi 2 Model B Rev 1.1 (`armv7l`, 32-bit, 921 MiB RAM,
Python 3.13.5) exact-wheel test remains `0.20.5.post2` (SHA-256
`2de6f2615f53e51cf7c90b05c564e027439946f3eec069780cd0404017814629`).
Heavier optional extras retain their own hardware requirements.

The release is wheel-only; no source distribution is published. Its public
PyPI provenance identifies `matttest0080-prog/hermes-agent-iot`, workflow
`publish-pypi.yml`, and environment `pypi`.

Use the native-compatible installer:

```bash
bash setup-pi2-minimal.sh --profile minimal
bash setup-pi2-minimal.sh --profile iot
bash setup-pi2-minimal.sh --profile rag
bash setup-pi2-minimal.sh --profile full   # stronger edge host only
bash setup-pi2-minimal.sh --profile dev    # contributor machine
```

Backward-compatible aliases are still accepted: `core` -> `minimal`, `native` -> `iot`.

Profiles:

- `minimal`: smallest practical Hermes CLI profile. Installs package through `pip install -e .[minimal]`, writes a config that disables heavy toolsets by default.
- `iot`: minimal plus MCP/ACP/Home Assistant/MQTT/SMS extras. Still disables browser/media/messaging tool surfaces by default.
- `rag`: iot plus Honcho optional dependency and a remote-first RAG configuration. It does not install a second unpinned document/vector package list.
- `full`: broader cross-platform Hermes extras for stronger Raspberry Pi, ARM64, x86 mini PC, VM, or NAS hosts.
- `dev`: full plus test/developer tooling.

## Optional integration security posture

Pi2/minimal and IoT profiles keep risky or heavy integrations opt-in:

- `website/` is for full/dev builds and should stay npm-audit clean.
- `plugins/platforms/photon/sidecar/` is a full-profile sidecar, not a Pi2/minimal default.
- `scripts/whatsapp-bridge/` is disabled by default because it is an experimental integration with a separate security and compatibility posture. Before enabling it on a production host, review the current Baileys advisories and bridge-specific configuration, run `npm run install:unsafe-baileys` inside `scripts/whatsapp-bridge/`, and start it with `HERMES_ENABLE_EXPERIMENTAL_WHATSAPP_BRIDGE=1`.

## Recommended Pi2 source install

Use this path instead of the lightweight PyPI wheel when repository-level
skills, optional MCP catalogs, locale files, Dashboard/TUI assets, or source
development files are required:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential cmake git

git clone --branch pi2-lite --depth 1 https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
bash setup-pi2-minimal.sh --profile minimal

source ~/.hermes-venv/bin/activate
hermes setup model
hermes
```

Hermes requires Python `>=3.11,<3.14`. If your Raspberry Pi OS image ships older Python, install Python 3.11+ first.

## Updating the Pi2 installation

The Pi2 installation tracks the `pi2-lite` branch and uses profile-specific
dependency sets. The examples below assume the repository was cloned into
`~/hermes-agent-iot`; if you used another clone directory, replace that path.
The `hermes` executable is installed in the Pi2 virtual environment created by
the installer. Opening the repository directory alone does **not** put it on
`PATH`; activate the environment before running any `hermes` command:

```bash
cd ~/hermes-agent-iot
source ~/.hermes-venv/bin/activate
command -v hermes
hermes --version
```

If Bash reports `hermes: command not found`, the virtual environment is not
active. Run the activation command above. If `~/.hermes-venv/bin/activate`
does not exist, complete the profile installation first:

```bash
bash setup-pi2-minimal.sh --profile minimal
source ~/.hermes-venv/bin/activate
```

Preview an update with the branch explicitly selected:

```bash
# Preview only; this does not install dependencies
hermes update --check --branch pi2-lite
```

In IoT release 0.20.4 and later, the updater detects the
`hermes-agent-iot` source, installed distribution, or install-profile record
and defaults a bare `hermes update` to `pi2-lite`. Keeping the branch explicit
in automation is still recommended because it makes the intended target
auditable.

For an actual Pi2 update, pull the selected branch and rerun the same profile
installer. This preserves the intended `minimal`, `iot`, or `rag` dependency
set:

```bash
cd ~/hermes-agent-iot

# Review local changes first; do not update a dirty checkout blindly.
git status --short

# Explicitly select the Pi2 branch before fetching or merging.
git switch pi2-lite
git fetch origin pi2-lite
git merge --ff-only origin/pi2-lite

source ~/.hermes-venv/bin/activate
bash setup-pi2-minimal.sh --profile minimal

# Verify that the checkout stayed on the Pi2 branch.
test "$(git branch --show-current)" = "pi2-lite"
git status --short
```

Replace `minimal` with the profile originally installed (`iot`, `rag`, `full`,
or `dev`). If you use the Hermes updater, the profile installer must be rerun
afterwards; specifying the branch explicitly remains the safest scripted form:

```bash
hermes update --branch pi2-lite --backup
bash setup-pi2-minimal.sh --profile minimal
```

The generic updater can reinstall a broader dependency group and is therefore
not the preferred Pi2 profile update path. The IoT-aware default prevents a
bare update from switching to `main`, but production Pi2 nodes should still use
the explicit source-update sequence above and rerun their selected profile.

Before and after updating, verify the branch and installation:

```bash
git branch --show-current       # expected: pi2-lite
git status --short
git log -1 --oneline
hermes --version
hermes doctor
```

For production or always-on Pi2 nodes, stop active Hermes gateways before
updating and preserve a backup when needed. Do not run `git reset --hard` or
switch to `main` as a routine update procedure.

## Robotics applications

This fork can be used as a lightweight robot edge agent: it coordinates high-level tasks, talks to MQTT/HTTP/serial/ROS bridge layers, summarizes robot state, and connects a remote/LAN AI model to the robot controller. Keep hard real-time motor control, obstacle reflexes, and emergency-stop enforcement in an MCU or ROS controller.

Recommended split:

```text
Cloud/LAN LLM or operator UI -> Hermes Agent IoT -> MQTT/HTTP/serial bridge -> MCU/ROS controller -> robot body
```

See `ROBOTICS.md` for recommended robot architectures, MQTT topic conventions, safety limits, watchdog tasks, and next implementation steps.

## MQTT IoT tools

The native and rag profiles explicitly select the lightweight `mqtt` toolset. Other profiles and platforms do not gain publish capability merely because `MQTT_HOST` exists. Configure a broker with:

```bash
export MQTT_HOST=192.168.1.10
export MQTT_PORT=8883
# Optional:
export MQTT_USERNAME=iot-user
export MQTT_PASSWORD=secret
export MQTT_CLIENT_ID=pi2-edge  # optional prefix; Hermes appends a unique suffix
export MQTT_TLS=true
hermes tools enable mqtt
```

Available MQTT tools:

- `mqtt_publish`: publish sensor values or device commands
- `mqtt_subscribe_recent`: listen briefly for retained/new messages on a topic filter
- `mqtt_device_command`: publish a command and optionally wait for a state/ack topic

MQTT brokers do not provide history by default. `mqtt_subscribe_recent` returns retained messages and messages published while the tool is listening. A password without a username fails closed, and credentials fail closed unless TLS is enabled. For an isolated, trusted plaintext lab network only, `MQTT_ALLOW_INSECURE_CREDENTIALS=true` is the explicit override. `MQTT_CLIENT_ID` is a prefix, not a fixed ID: Hermes adds a process/random suffix so concurrent tool calls do not disconnect each other. To protect Pi2 memory, inbound messages larger than 64 KiB and messages that would push one tool response past 256 KiB of payload data are dropped and reported in the response.

Use a dedicated broker account with TLS and topic ACLs. Grant sensor topics read-only access and restrict actuator command topics to the smallest required prefix. Hard real-time and emergency-stop paths must remain in the MCU/PLC/ROS controller.

## Local llama.cpp / OpenAI-compatible model

Pi2 can connect to a local or LAN OpenAI-compatible endpoint. For example, if `llama.cpp` server is running at `http://localhost:8080/v1`, configure Hermes through:

```bash
hermes setup model
# Select: Local AI (llama.cpp / llama-server)
```

For the complete SD-card GGUF, llama-server, systemd, and remote-primary/local-fallback procedure, see [RASPBERRY_PI2_MANUAL.md](RASPBERRY_PI2_MANUAL.md).
Important: a 7B model on Raspberry Pi 2 is usually impractical because of RAM and speed. Prefer:

- a remote/OpenRouter/OpenAI-compatible provider, or
- a much smaller quantized model, or
- a stronger LAN machine running `llama.cpp` with Pi2 acting as the Hermes client.

## Context and performance defaults

Upstream Hermes keeps a 64K runtime-context floor for reliable full tool use with local/Ollama models. The Pi2 profiles lower that floor through `agent.minimum_tool_context_length` so small local models can still run in a degraded, low-tool mode:

- `config.pi2-core.yaml`: `2048` tokens for tiny local chat / minimal tools
- `config.pi2-native.yaml`: `8192` tokens for broader native workflows
- `config.pi2-rag.yaml`: `8192` tokens locally, with remote/central RAG preferred

For full Hermes tool use, coding, or shared RAG, keep using a stronger LAN/cloud model with 64K+ context. The Pi2 override is an escape hatch for constrained local inference, not a claim that 2K can carry the complete Hermes tool surface.

## Memory and RAG posture

Default Pi2 memory:

- built-in Hermes memory
- session search
- SQLite/FTS-style lightweight local state

Optional RAG:

```bash
bash setup-pi2-minimal.sh --profile rag
```

The RAG profile intentionally avoids installing `torch`, `sentence-transformers`, `chromadb`, `sqlite-vec`, or a second unpinned document-helper list. For Pi2, use built-in SQLite/FTS memory plus remote embeddings or cloud memory providers. The IoT branch also uses plain `uvicorn` instead of `uvicorn[standard]` to avoid `uvloop` source builds on ARMv7. Run local embeddings/vector indexing only on a stronger central node.

## Multi-Pi2 shared memory / RAG architecture

For multiple Raspberry Pi 2 nodes, use the Pi2 devices as lightweight Hermes clients and put shared memory/RAG on a stronger central node. Do not run a full local embedding/vector stack on every Pi2.

Recommended layout:

```text
Pi2 kitchen ┐
Pi2 lab     ├── HTTP/LAN API ──> shared memory/RAG server
Pi2 garage  ┘                    ├── SQLite/Postgres memory store
                                  ├── embedding provider or LAN embedding model
                                  └── Qdrant/Chroma/pgvector vector index
```

Pi2 nodes should:

- run Hermes Agent with the core/native/rag Pi2 profile
- keep local short-term/session state lightweight
- send memory writes, document ingests, and RAG queries to the central API
- avoid local `torch`, `sentence-transformers`, and `chromadb`

The central node can be an x86 mini PC, NAS, Pi 4/5, VM, or cloud host. It should own embedding, vector indexing, deduplication, backups, and cross-device memory policy.

Use metadata on every shared memory/RAG item so nodes do not pollute one another's context:

```json
{
  "device_id": "pi2-kitchen",
  "scope": "global|device|room|user",
  "source": "conversation|note|sensor|manual",
  "created_at": "2026-06-25T00:00:00Z"
}
```

First implementation recommendation:

- start with a tiny central HTTP service backed by SQLite FTS5 for keyword search
- add remote embeddings and Qdrant/pgvector later only if semantic search is needed
- never mount one writable SQLite database over NFS/Samba for many Pi2 nodes; use an API or per-device local DBs that sync into the central server

## Config templates

Installer templates live in:

```text
templates/config.pi2-core.yaml
templates/config.pi2-native.yaml
templates/config.pi2-rag.yaml
```

The installer copies one to `~/.hermes/config.yaml` only if that file does not already exist. Existing configs are not overwritten.

## Re-enabling features later

Use native Hermes controls:

```bash
hermes tools
hermes tools list
hermes tools enable browser
hermes tools enable image_gen
hermes config edit
```

Then install any missing extra dependencies shown by the feature/tool.

## Verification

After installation:

```bash
source ~/.hermes-venv/bin/activate
hermes --help
python -m py_compile cli.py run_agent.py model_tools.py toolsets.py
python - <<'PY'
from toolsets import resolve_toolset
print('hermes-cli tools:', len(resolve_toolset('hermes-cli')))
print('file tools:', resolve_toolset('file'))
PY
```

## Design rule

Allowed Pi2 slimming:

- default-off toolsets
- optional extras
- lazy imports/lazy install
- profile-specific config
- documentation of heavy paths

Avoided:

- deleting core modules
- patching source during install
- removing toolset definitions
- forking config schema
- hard-coding Pi2-only behavior into generic runtime paths
