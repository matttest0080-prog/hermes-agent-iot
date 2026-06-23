# Hermes Agent on Raspberry Pi 2 (ARMv7 32-bit)

<p align="center">
  <img src="assets/hermes-icon-white.svg" alt="Hermes Agent" width="100">
</p>

## Overview

This is a minimal CLI version of **Hermes Agent** optimized for **Raspberry Pi 2** (ARMv7 32-bit, 1GB RAM).

This fork is based on [Hermes Agent by Nous Research](https://github.com/NousResearch/hermes-agent),
modified to run on constrained ARMv7 hardware with only 1GB RAM.

**Key Features:**
- ✅ CLI-only interface (no TUI/web UI)
- ✅ Optimized for 1GB RAM
- ✅ Works with local LLM via lm-studio or llama.cpp
- ✅ Memory & RAG support (sqlite-vec + sentence-transformers)

## Original Hermes Agent

Hermes Agent is an open-source AI agent by **Nous Research** that:

- Creates skills from experience
- Improves them during use
- Runs across CLI, TUI, web dashboard, and Electron app
- Maintains conversation caching for efficiency

**Repository**: https://github.com/NousResearch/hermes-agent

**License**: MIT

## Hardware Requirements

| Component | Requirement |
|-----------|-------------|
| Device | Raspberry Pi 2 Model B |
| CPU | ARMv7 900MHz (4 cores) |
| RAM | 1GB LPDDR2 (minimum) |
| Storage | microSD card (≥8GB) |
| OS | Raspberry Pi OS Lite (32-bit) |

## Quick Install

### Step 1: Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv build-essential git wget
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv ~/.hermes-venv
source ~/.hermes-venv/bin/activate
pip install --upgrade pip
```

### Step 3: Install Hermes Agent (Pi2 Minimal)

```bash
git clone https://github.com/Matt0080828/hermes-agent-iot.git
cd hermes-agent-iot
bash setup-pi2.sh
```

### Step 4: Install RAG Dependencies (Pi2 Optimized)

**Note**: For Raspberry Pi 2 (1GB RAM), RAG dependencies are already installed in `setup-pi2.sh`.
Skip this step unless you need to manually install.

```bash
# Already included in setup-pi2.sh: honcho, chromadb, sentence-transformers, pypdf, beautifulsoup4
# If manual install needed:
pip install honcho-ai chromadb sentence-transformers pypdf beautifulsoup4
```

### Step 5: Configure Hermes

```bash
# Create config directory
mkdir -p ~/.hermes

# Create config file
cat > ~/.hermes/config.yaml << 'EOF'
# Hermes Agent config for Raspberry Pi 2 (ARMv7 32-bit, 1GB RAM)
# Based on hermes-agent 0.17.0

models:
  default: "custom:qwen2.5-7b"
  provider: custom
  base_url: "http://localhost:8080/v1"

providers:
  custom:
    base_url: "http://localhost:8080/v1"
    api_key: "not-used"
    models:
      - "qwen2.5-7b"

fallback_providers: []

toolsets:
  - hermes-cli

agent:
  max_turns: 150

memory:
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  provider: honcho
  nudge_interval: 10
  flush_min_turns: 6

display:
  compact: false
  personality: concise

terminal:
  backend: local
  timeout: 180

web:
  backend: ""
  search_backend: ""
  extract_backend: ""

browser:
  inactivity_timeout: 120

compression:
  enabled: true
  threshold: 0.5

kanban:
  dispatch_in_gateway: true

prompt_caching:
  cache_ttl: 5m

openrouter:
  response_cache: true

display:
  personality: concise
  skin: default

logging:
  level: INFO

sync_config:
  hermes_agent_version: "0.17.0"
EOF
```

## Model Setup Options

### Option A: lm-studio (Recommended for Pi2)

**Architecture**: Run lm-studio on a powerful machine (x86_64), connect to it from Pi2.

**Setup**:

1. **On x86_64 machine (hosting model)**:
   ```bash
   # Download lm-studio for Linux (or Windows/Mac)
   # Launch lm-studio → Load model → Start Server
   # Default port: 1234
   ```

2. **On Raspberry Pi 2 (client)**:
   - Find the x86_64 machine IP (e.g., `192.168.1.100`)
   - Update `~/.hermes/config.yaml`:
   ```yaml
   models:
     default: "custom:qwen2.5-7b"
     provider: custom
     base_url: "http://192.168.1.100:1234/v1"

   providers:
     custom:
       base_url: "http://192.168.1.100:1234/v1"
   ```

### Option B: llama.cpp (Advanced - for x86_64 only)

**Note**: llama.cpp compilation on Pi2 is extremely slow (~1-2 hours). Recommended to run on x86_64 and connect remotely.

1. **Compile llama.cpp** (on x86_64 machine):
   ```bash
   git clone https://github.com/ggerganov/llama.cpp.git
   cd llama.cpp
   make clean
   make -j$(nproc) LLAMA_AVX2=OFF LLAMA_AVX=OFF LLAMA_F16C=OFF LLAMA_FMA=OFF
   ```

2. **Download Qwen2.5-7B GGUF model**
   ```bash
   pip install huggingface_hub
   huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF \
       qwen2.5-7b-instruct-q4_k_m.gguf \
       --local-dir ~
   ```

3. **Start server**
   ```bash
   cd ~/llama.cpp
   ./server -m ~/qwen2.5-7b-instruct-q4_k_m.gguf \
       -c 2048 \
       --port 8080 \
       -np 1 \
       --n_gpu_layers 0
   ```

## Usage

```bash
# Activate virtual environment
source ~/.hermes-venv/bin/activate

# Change to Hermes directory
cd ~/hermes-agent-iot

# Start Hermes
hermes
```

In Hermes CLI:
```
/hermes tools list
```

Expected output:
```
✓ enabled  memory          💾 Memory
✓ enabled  skills          🛠 Skills
✓ enabled  terminal        🖥 Terminal
✓ enabled  session_search  🔍 Session Search
```

## Memory Optimization

If you encounter memory issues (1GB RAM):

```yaml
# ~/.hermes/config.yaml
memory:
  memory_char_limit: 1000   # Reduced from 2200
  user_char_limit: 500      # Reduced from 1375
```

Or use smaller model:
```bash
# Download Qwen2.5-1.5B (smaller, ~2GB RAM)
huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GGUF \
    qwen2.5-1.5b-instruct-q4_k_m.gguf \
    --local-dir ~

# Start server with smaller context
./server -m ~/qwen2.5-1.5b-instruct-q4_k_m.gguf -c 1024 --port 8080
```

## Tags

| Tag | Description |
|-----|-------------|
| `v0.1-pi2` | Initial Pi2 support |
| `v0.2-pi2` | Added installation manual |
| `v0.3-pi2` | Added quick migration script |
| `v0.4-pi2` | Minimal CLI only (35MB) |
| `v0.5-pi2` | RAG SQLite backend + uvloop fix |
| `v0.6-pi2` | Remove uvloop/fastapi, use asyncio |
| `v0.7-pi2` | Replace chromadb with honcho-ai for RAG |
| `v0.8-pi2` | Add explicit httpx install in setup script |
| `v0.9-pi2` | Add Nous Research origin attribution |
| `v10.0-pi2` | Add SYNC_STRATEGY.md for hermes-agent 0.17.0 sync process |
| `v11.0-pi2` | Remove Docker deps, add setup-pi2.sh, Pi2 minimal config |

## Repository

- **GitHub**: https://github.com/Matt0080828/hermes-agent-iot
- **Tags**: `v11.0-pi2` (latest) |

## Sync Strategy

This repository is maintained as a **minimal CLI version** for Raspberry Pi 2 (ARMv7 32-bit, 1GB RAM).

For updates from the main Hermes Agent repository:
- See [`SYNC_STRATEGY.md`](./SYNC_STRATEGY.md) for the full merge process
- Latest sync target: `hermes-agent 0.17.0`

## Notes

- Raspberry Pi 2 is **32-bit ARM**, ensure all software supports ARMv7
- This is a **CLI-only** version (no TUI/web UI)
- Memory usage: ~500-800MB depending on model size
- Use quantized models (q4_k_m, q5_k_m) to reduce RAM usage

---

**Author**: Matt0080828  
**Based on**: [Hermes Agent by Nous Research](https://github.com/NousResearch/hermes-agent)
