# Hermes Agent on Raspberry Pi 2 (ARMv7 32-bit)

This fork adds support for Raspberry Pi 2 (32-bit ARM).

## Key Changes

- **llama.cpp**: Compiled with NEON support, disabled AVX/AVX2
- **sqlite-vec**: SQLite vector extension for RAG
- **RAG**: Uses `all-MiniLM-L6-v2` (ARM-optimized)
- **Model**: Qwen2.5-7B (GGUF q4_k_m, ~4.6GB)

## Installation on Raspberry Pi 2

```bash
# Install dependencies
sudo apt update && sudo apt install -y python3 python3-pip python3-venv build-essential git wget

# Create venv
python3 -m venv ~/.hermes-venv
source ~/.hermes-venv/bin/activate

# Install deps
pip install --upgrade pip
pip install honcho-ai sentence-transformers pypdf beautifulsoup4

# Build llama.cpp for ARMv7
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make -j$(nproc) LLAMA_AVX2=OFF LLAMA_AVX=OFF LLAMA_F16C=OFF LLAMA_FMA=OFF

# Download Qwen2.5-7B GGUF
wget https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf

# Install hermes-agent
git clone https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
pip install -e .

# Configure
hermes setup
```

## Configuration (`~/.hermes/config.yaml`)

```yaml
models:
  - name: "custom:qwen2.5-7b"
    base_url: "http://localhost:8080/v1"
    api_key: "not-used"

providers:
  - name: "custom"
    provider: "openai_compatible"
    base_url: "http://localhost:8080/v1"
    api_key: "not-used"

memory:
  provider: "honcho"  # SQLite backend, lightweight
```

## Start Server & Agent

```bash
# Terminal 1: Start llama.cpp server
cd llama.cpp && ./server -m qwen2.5-7b-instruct-q4_k_m.gguf -c 2048 --port 8080

# Terminal 2: Run hermes-agent
cd new_agent && hermes
```

## Memory

Store: `~/work/work_RAG/.chromadb/chroma.sqlite3` (SQLite)

## RAG

```bash
pip install chromadb sentence-transformers pypdf beautifulsoup4
```
