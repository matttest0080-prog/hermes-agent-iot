# Hermes Agent on Raspberry Pi 2 (ARMv7 32-bit)
## 安裝與操作手冊

---

## 目錄
1. [硬體與系統需求](#硬體與系統需求)
2. [安裝步驟](#安裝步驟)
3. [使用 lm-studio (推薦)](#使用-lm-studio-推薦)
4. [使用 llama.cpp (進階)](#使用-llamacpp-進階)
5. [常見問題](#常見問題)

---

## 硬體與系統需求

| 項目 | 規格 |
|------|------|
| 裝置 | Raspberry Pi 2 Model B |
| CPU | ARMv7 900MHz (4 cores) |
| RAM | 1GB LPDDR2 |
| 存儲 | microSD 卡 (至少 8GB) |
| OS | Raspberry Pi OS Lite (32-bit) |

**注意：** Raspberry Pi 2 為 32-bit ARM 架構，不支援 64-bit 軟體。

---

## 安裝步驟

### 1. 更新系統

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv build-essential git wget
```

### 2. 建立虛擬環境

```bash
python3 -m venv ~/.hermes-venv
source ~/.hermes-venv/bin/activate
pip install --upgrade pip
```

### 3. 安裝 Hermes Agent 依賴

```bash
pip install honcho-ai sentence-transformers pypdf beautifulsoup4
```

---

## 使用 lm-studio (推薦)

### 優點
- ✅ 圖形化介面，易於操作
- ✅ 無需編譯 llama.cpp
- ✅ 支援模型熱切換
- ✅ 內建模型下載功能

### 缺點
- ⚠️ 需要圖形界面（桌面環境）

### 安裝 lm-studio

```bash
# 下載 lm-studio for Linux
wget https://github.com/lmstudio-ai/lmstudio/releases/download/v0.4.0/lmstudio_0.4.0_amd64.deb
sudo dpkg -i lmstudio_0.4.0_amd64.deb
```

**注意：** Raspberry Pi 2 為 ARMv7，需編譯 lm-studio 或使用 Web 版本。

### 替代方案：使用 Web API (推薦)

#### 1. 安裝 llama.cpp Web Server (ARMv7)

```bash
# Clone llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# 編譯 (禁用 AVX/AVX2，啟用 NEON)
make clean
make -j$(nproc) LLAMA_AVX2=OFF LLAMA_AVX=OFF LLAMA_F16C=OFF LLAMA_FMA=OFF server

cd ..
```

#### 2. 下載 Qwen2.5-7B GGUF 模型

```bash
# 使用 huggingface-cli 下載
pip install huggingface_hub

# 下載模型（q4_k_m 量化版，約 4.6GB）
huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF \
    qwen2.5-7b-instruct-q4_k_m.gguf \
    --local-dir ~
```

#### 3. 啟動 llama.cpp 服務

```bash
cd ~/llama.cpp
./server -m ~/qwen2.5-7b-instruct-q4_k_m.gguf \
    -c 2048 \
    --port 8080 \
    -np 1 \
    --n_gpu_layers 0
```

**參數說明：**
- `-c 2048`: context size (樹莓派 2 RAM 限制)
- `--n_gpu_layers 0`: 不使用 GPU (樹莓派 2 無 CUDA)

#### 4. 測試 API

```bash
curl http://localhost:8080/v1/models
```

應返回：
```json
{
  "data": [
    {
      "id": "qwen2.5-7b-instruct-q4_k_m",
      "object": "model"
    }
  ]
}
```

#### 5. 配置 Hermes Agent

```bash
# 建立設定檔
cat > ~/.hermes/config.yaml << 'EOF'
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
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  provider: "honcho"
  nudge_interval: 10
  flush_min_turns: 6

tools:
  - memory
  - skills
  - terminal
  - session_search
EOF
```

#### 6. 安裝 Hermes Agent

```bash
git clone https://github.com/Matt0080828/new_agent.git
cd new_agent
pip install -e .
```

#### 7. 啟動 Hermes Agent

```bash
source ~/.hermes-venv/bin/activate
hermes
```

---

## 使用 llama.cpp (進階)

### 優點
- ✅ 純命令列，無圖形界面需求
- ✅ 更佳的資源控制
- ✅ 支援 GPU 加速 (Raspberry Pi 2 無效)

### 缺點
- ⚠️ 需要編譯 (耗時約 15-30 分鐘)
- ⚠️ 需要手動管理模型

### 安裝步驟

#### 1. 編譯 llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# 編譯 (ARMv7 32-bit)
make clean
make -j$(nproc) LLAMA_AVX2=OFF LLAMA_AVX=OFF LLAMA_F16C=OFF LLAMA_FMA=OFF

# 測試編譯
./llama-cli --version
```

#### 2. 下載模型

```bash
# 使用 huggingface-cli
pip install huggingface_hub

# 下載 Qwen2.5-7B (q4_k_m 量化)
huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF \
    qwen2.5-7b-instruct-q4_k_m.gguf \
    --local-dir ~
```

#### 3. 啟動 Server

```bash
cd ~/llama.cpp
./server -m ~/qwen2.5-7b-instruct-q4_k_m.gguf \
    -c 2048 \
    --port 8080 \
    -np 1
```

#### 4. 測試

```bash
curl http://localhost:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen2.5-7b-instruct-q4_k_m",
        "messages": [{"role": "user", "content": "Hello!"}],
        "temperature": 0.7
    }'
```

---

## 常見問題

### Q1: 編譯 llama.cpp 時記憶體不足？

**解決方案：** 使用更少的核心
```bash
make -j2 LLAMA_AVX2=OFF LLAMA_AVX=OFF  # 僅使用 2 個核心
```

### Q2: 模型載入失敗？

**原因：** GGUF 模型過大 (4.6GB)，超出 RAM
**解決方案：**
- 使用更小的模型 (如 `qwen2.5-1.5B`)
- 使用 `--n_ctx` 參數減少 context size

```bash
./server -m ~/qwen2.5-1.5b-instruct-q4_k_m.gguf -c 1024 --port 8080
```

### Q3: hermes 启动时显示 no module named .honcho-ai.？

**解決方案：**
```bash
source ~/.hermes-venv/bin/activate
pip install honcho-ai sentence-transformers pypdf beautifulsoup4
```

### Q4: 如何設定記憶體限制？

在 `~/.hermes/config.yaml` 中調整：
```yaml
memory:
  memory_char_limit: 1500   # 減少記憶體使用
  user_char_limit: 800
```

---

## 快速啟動腳本

### start_lm_server.sh
```bash
#!/bin/bash
# 啟動 llama.cpp 服務

cd ~/llama.cpp
./server -m ~/qwen2.5-7b-instruct-q4_k_m.gguf \
    -c 2048 \
    --port 8080 \
    -np 1 \
    --n_gpu_layers 0
```

### start_hermes.sh
```bash
#!/bin/bash
# 啟動 Hermes Agent

cd ~/new_agent
source ~/.hermes-venv/bin/activate
hermes
```

### 使用方式
```bash
# Terminal 1 - 啟動模型服務
chmod +x start_lm_server.sh
./start_lm_server.sh

# Terminal 2 - 啟動 Hermes
chmod +x start_hermes.sh
./start_hermes.sh
```

---

## 驗證測試

在 Hermes CLI 中輸入：
```
/hermes tools list
```

應顯示：
```
✓ enabled  memory          💾 Memory
✓ enabled  skills          🛠 Skills
✓ enabled  terminal        🖥 Terminal
✓ enabled  session_search  🔍 Session Search
```

---

## 注意事項

1. **樹莓派 2 為 32-bit ARM**，請確保所有軟體均支援 ARMv7
2. **記憶體有限** (1GB)，避免同時運行多個模型
3. **使用量化模型** (q4_k_m, q5_k_m) 減少記憶體使用
4. **使用虛擬環境** 避免系統 Python 衝突

---

**版本**: v0.2-pi2  \
**作者**: Matt0080828  \
**Repository**: https://github.com/Matt0080828/new_agent

---

## 快速遷移腳本 (New Machine)

### 一键迁移到新 Raspberry Pi 2

```bash
#!/bin/bash
# setup_pi2_hermes.sh - Quick setup for Raspberry Pi 2

set -e

echo "=== Hermes Agent Quick Setup for Pi2 ==="

# Step 1: Update system
echo "Step 1: Updating system..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv build-essential git wget

# Step 2: Clone hermes-agent (shallow)
echo "Step 2: Cloning hermes-agent (shallow)..."
git clone --depth=1 https://github.com/Matt0080828/new_agent.git ~/new_agent

# Step 3: Create virtual environment
echo "Step 3: Creating virtual environment..."
python3 -m venv ~/.hermes-venv
source ~/.hermes-venv/bin/activate

# Step 4: Install hermes-agent
echo "Step 4: Installing hermes-agent..."
cd ~/new_agent
pip install -e .

# Step 5: Install RAG dependencies
echo "Step 5: Installing RAG dependencies..."
pip install honcho-ai sentence-transformers pypdf beautifulsoup4

# Step 6: Setup config
echo "Step 6: Creating config..."
mkdir -p ~/.hermes
cat > ~/.hermes/config.yaml << 'EOF'
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
  memory_enabled: true
  user_profile_enabled: true
  memory_char_limit: 2200
  user_char_limit: 1375
  provider: "honcho"
  nudge_interval: 10
  flush_min_turns: 6

tools:
  - memory
  - skills
  - terminal
  - session_search
EOF

echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Build llama.cpp: cd ~/ && git clone https://github.com/ggerganov/llama.cpp.git && cd llama.cpp && make -j\$(nproc) LLAMA_AVX2=OFF LLAMA_AVX=OFF"
echo "2. Download model: huggingface-cli download Qwen/Qwen2.5-7B-Instruct-GGUF qwen2.5-7b-instruct-q4_k_m.gguf --local-dir ~"
echo "3. Start server: cd ~/llama.cpp && ./server -m ~/qwen2.5-7b-instruct-q4_k_m.gguf -c 2048 --port 8080"
echo "4. Run hermes: cd ~/new_agent && source ~/.hermes-venv/bin/activate && hermes"
```

### 記憶體優化設定 (1GB RAM)

若系統記憶體不足，調整 `~/.hermes/config.yaml`：

```yaml
memory:
  memory_char_limit: 1000   # 減少記憶體使用
  user_char_limit: 500
```

### 使用更小模型 (512MB RAM)

```bash
# 下載更小的模型
huggingface-cli download Qwen/Qwen2.5-1.5B-Instruct-GGUF \
    qwen2.5-1.5b-instruct-q4_k_m.gguf \
    --local-dir ~

# 啟動服務
./server -m ~/qwen2.5-1.5b-instruct-q4_k_m.gguf -c 1024 --port 8080
```
