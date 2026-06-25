# Hermes Agent IoT / Pi2 Edition

<p align="center">
  <img src="assets/hermes-icon-white.svg" alt="Hermes Agent" width="100">
</p>

This repository is a Raspberry Pi 2 / IoT install profile for the original Hermes Agent project. It tracks Hermes Agent code while keeping this fork's default install path lightweight for small ARM/Linux devices.

## Repository lineage

Current target repository:

```text
https://github.com/matttest0080-prog/hermes-agent-iot
```

Local source used for the latest sync:

```text
/home/matt/work/matt0080/hermes-agent-iot
```

Upstream project:

```text
https://github.com/NousResearch/hermes-agent
```

Latest integrated source commit:

```text
b273e7129 chore: sync IoT main with Hermes 0.17.0
```

## Positioning

This is intended to be a native-compatible Pi2 profile, not a rewritten mini-agent.

The goal is:

- keep Hermes Agent's native architecture and package layout
- keep CLI, tools, skills, memory, session search, cron, delegation, MCP, ACP, gateway, plugins, and provider adapters available
- make the default Pi2 install avoid heavy dependencies and heavy default tool surfaces
- preserve this repository's slim IoT checkout by excluding desktop app, website, large docs/test trees, and CI artifacts from the target branch
- let users re-enable features later through standard Hermes commands

## Quick install

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential git

git clone --depth 1 https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
bash setup-pi2-minimal.sh --profile core

source ~/.hermes-venv/bin/activate
hermes setup model
hermes
```

Hermes requires Python `>=3.11,<3.14`.

## Install profiles

```bash
bash setup-pi2-minimal.sh --profile core
bash setup-pi2-minimal.sh --profile native
bash setup-pi2-minimal.sh --profile rag
```

- `core`: smallest practical CLI profile. Heavy browser/media/platform toolsets are disabled by default.
- `native`: broader native profile with MCP/ACP/Home Assistant/SMS extras installed, still default-off for heavy tool surfaces.
- `rag`: native profile plus lightweight document/RAG helpers. Remote embeddings/cloud memory are recommended on Pi2.

## What changed for Pi2

The Pi2 installer uses Hermes' native Python package metadata:

```bash
python -m pip install -e ".[cli,pty]"
```

or a broader extras set depending on profile. It does not hand-maintain a separate dependency list and does not patch source files during install.

The installer writes a Pi2 config template only when `~/.hermes/config.yaml` does not already exist:

```text
templates/config.pi2-core.yaml
templates/config.pi2-native.yaml
templates/config.pi2-rag.yaml
```

## Default-off heavy features

The Pi2 config disables these toolsets by default where appropriate:

- browser
- uvloop / `uvicorn[standard]` (web API/dashboard use uvicorn's native Python asyncio mode)
- image/video generation
- TTS/STT-style voice features
- computer_use
- messaging platform tools
- Discord/Feishu/Yuanbao/Spotify/Home Assistant depending on profile
- experimental heavy reasoning/toolsets

The core code remains present. Re-enable features later with:

```bash
hermes tools
hermes tools enable browser
hermes tools enable image_gen
```

and install any required extras when prompted.

For Pi2, do not install `uvicorn[standard]`; it pulls `uvloop`, which is not reliable on ARMv7/Pi2. If you need web API/dashboard dependencies manually, use:

```bash
pip install fastapi uvicorn python-multipart
```

## Memory and RAG

Default Pi2 posture:

- use built-in Hermes memory and session search
- avoid `torch`, `sentence-transformers`, and `chromadb` by default
- prefer remote embeddings or cloud memory providers for semantic RAG

For multiple Pi2 devices, use each Pi2 as a lightweight Hermes client and share memory/RAG through a central LAN/cloud service:

```text
Pi2 nodes -> HTTP API -> shared memory/RAG server -> SQLite/Postgres + optional Qdrant/pgvector
```

The central server should handle embeddings, vector indexing, backups, deduplication, and cross-device scope metadata such as `device_id`, `room`, and `global|device|user`. Avoid having multiple Pi2 nodes write directly to one SQLite database over NFS/Samba.

For optional RAG helpers:

```bash
bash setup-pi2-minimal.sh --profile rag
```

See `README_PI2.md` for details.

## Local model note

Pi2 can use a local or LAN OpenAI-compatible server such as `llama.cpp`, but a 7B model directly on a Raspberry Pi 2 is usually too slow and memory constrained. A practical setup is often:

- Pi2 runs Hermes Agent CLI/profile
- another machine or remote provider runs the LLM endpoint
- Hermes connects through OpenAI-compatible API config

## Verification

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

## License

Hermes Agent is MIT licensed. See `LICENSE`.
