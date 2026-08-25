<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent IoT" width="100%">
</p>

# Hermes Agent IoT

> 面向 Raspberry Pi 2 / ARMv7、MQTT、Home Assistant、机器人和低资源边缘 AI 的轻量级 Hermes Agent。

<p align="center">
  <a href="https://pypi.org/project/hermes-agent-iot/"><img src="https://img.shields.io/badge/PyPI-hermes--agent--iot-blue?style=for-the-badge" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Upstream-NousResearch%2Fhermes--agent-blueviolet?style=for-the-badge" alt="Upstream Hermes Agent"></a>
  <a href="README_PI2.md"><img src="https://img.shields.io/badge/Raspberry%20Pi%202-ARMv7-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white" alt="Raspberry Pi 2"></a>
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/Lang-English-lightgrey?style=for-the-badge" alt="English"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
</p>

Hermes Agent IoT 是 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) 面向 IoT／机器人方向的 fork。维护中的 `pi2-lite` 分支专注于受限的 Raspberry Pi 与边缘部署，同时保留上游 Hermes Agent 的运行时与生态。

## 为什么选择 Hermes Agent IoT？

- **Raspberry Pi 2 / ARMv7：** 已验证的 1 GB 级硬件低资源安装路径。
- **IoT profiles：** 面向 MQTT、Home Assistant、MCP/ACP 与 remote-first RAG 的依赖配置。
- **边缘优先部署：** 将重型 AI 推理留在远端，由 Raspberry Pi 负责 Agent 编排与设备集成。
- **机器人方向：** 为 GPIO、I2C、PWM、传感器、执行器与机器人技能奠定基础。
- **上游感知：** IoT 与 ARMv7 兼容性改动与快速迭代的上游开发分开评审。

## 快速开始 — Raspberry Pi 2

Hermes Agent IoT 需要 Python `>=3.11,<3.14`。在虚拟环境中安装：

```bash
python3 --version
python3 -m venv ~/.venvs/hermes-iot
source ~/.venvs/hermes-iot/bin/activate
python -m pip install --upgrade pip
python -m pip install 'hermes-agent-iot[minimal]==0.20.5.post2'
python -m pip check

hermes-iot setup --profile minimal
hermes-iot profile show
hermes setup model
hermes
```

> 不要使用 system pip、`sudo pip` 或 `--break-system-packages`。

### 源码检出

当你需要完整的仓库资源时，使用维护中的 `pi2-lite` 分支：

```bash
git clone --branch pi2-lite --depth 1 \
  https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
bash setup-pi2-minimal.sh --profile minimal
source ~/.hermes-venv/bin/activate
hermes setup model
hermes
```

> 请保留 clone 目录。源码安装器使用可编辑的 Python 安装，移动或删除 checkout 会破坏环境。

## 安装 Profiles

| Profile | 目标 |
| --- | --- |
| `minimal` | Raspberry Pi 2 / ARMv7 / 1 GB 基线 |
| `iot` | MQTT、Home Assistant、MCP/ACP 及相关 IoT 集成 |
| `rag` | IoT 加上 Honcho / remote-first RAG |
| `full` | 更强的 Raspberry Pi、ARM64、x86 边缘服务器或 VM |
| `dev` | 贡献者与开发系统 |

让 PyPI extra 与 setup profile 保持一致。例如：

```bash
python -m pip install 'hermes-agent-iot[iot]==0.20.5.post2'
hermes-iot setup --profile iot
```

`full` 和 `dev` 不推荐用于 Raspberry Pi 2 / 1 GB 系统。

## 项目状态

| 能力 | 状态 |
| --- | --- |
| Raspberry Pi 2 / ARMv7 minimal 安装 | ✅ 已验证 |
| 公开 PyPI 包 | ✅ 可用 |
| Minimal 依赖配置 | ✅ 可用 |
| IoT 依赖配置 | ✅ 可用 |
| MQTT 集成 | ✅ 可用 |
| Home Assistant 集成 | ✅ 可用 |
| Remote-first RAG | ✅ 可用 |
| 机器人文档 | ✅ 可用 |
| GPIO 抽象 | 🛠 路线图 |
| I2C 设备层 | 🛠 路线图 |
| PWM / 舵机控制 | 🛠 路线图 |
| 传感器插件框架 | 🛠 路线图 |
| ESP32 MQTT 桥接 | 🛠 路线图 |

## 文档

- [IoT 项目概览](IOT_PROJECT.md) — 项目目标、支持状态、profiles 与路线图。
- [Raspberry Pi 2 快速开始](README_PI2.md) — 依赖矩阵、配置 profiles 与 Pi2 安全指引。
- [Raspberry Pi 2 手册](RASPBERRY_PI2_MANUAL.md) — 详细的 Pi2 部署文档。
- [机器人](ROBOTICS.md) — 机器人集成说明。
- [安全政策](SECURITY.md) — 漏洞报告与安全指引。
- [上游 Hermes Agent 文档](https://hermes-agent.nousresearch.com/docs/) — 通用 Hermes Agent 功能、providers、gateway、桌面/服务器用法与集成。

## 上游 vs Hermes Agent IoT

| 领域 | 上游 Hermes Agent | Hermes Agent IoT |
| --- | --- | --- |
| 通用桌面/服务器 Agent | 主要目标 | 使用上游基础 |
| Raspberry Pi 2 / ARMv7 | 非主要目标 | 主要兼容目标 |
| 1 GB 级 minimal profile | 通用依赖模型 | 专属 `minimal` profile |
| MQTT / Home Assistant 部署 | 通用集成 | 专属 `iot` profile |
| 低资源边缘部署 | 通用运行时 | fork 的核心重点 |
| 机器人 | 通用 Agent 范围 | 面向 IoT/机器人的文档与路线图 |

在依赖变更、IoT 补丁与 ARMv7 兼容性经过评审与验证期间，此 fork 可能有意落后于上游 `main`。对于通用桌面/服务器 Hermes Agent 用途，请优先使用上游项目。

## 已验证版本

当前已验证基线：

- PyPI: [`hermes-agent-iot 0.20.5.post2`](https://pypi.org/project/hermes-agent-iot/0.20.5.post2/)
- Tag: `iot-v0.20.5.post2`
- Python: `>=3.11,<3.14`
- 物理验证：Raspberry Pi 2 Model B Rev 1.1，32-bit ARMv7，921 MiB RAM，Python 3.13.5

`minimal` wheel 基线已在实体 Raspberry Pi 2 硬件上 clean-install 并 smoke test。更重的可选 extras 需要与其依赖集相匹配的硬件。

## 更新 Pi2 源码安装

始终将更新固定到 `pi2-lite` 分支：

```bash
cd ~/hermes-agent-iot
source ~/.hermes-venv/bin/activate

git status --short
git switch pi2-lite
git fetch origin pi2-lite
git merge --ff-only origin/pi2-lite

bash setup-pi2-minimal.sh --profile minimal
```

将 `minimal` 替换为最初安装的 profile。在 IoT release 0.20.4 及之后，裸 `hermes update` 会检测到 `hermes-agent-iot` distribution 并默认使用 `pi2-lite`；在自动化中显式的 `--branch pi2-lite` 仍有助于审计。源码更新后请重新运行 profile 安装器。

## 路线图

- [x] Raspberry Pi 2 / ARMv7 安装路径
- [x] 低资源依赖配置
- [x] IoT 依赖配置
- [x] MQTT / Home Assistant 集成路径
- [x] 公开 PyPI 包
- [x] 实体 Raspberry Pi 2 验证
- [ ] GPIO 抽象
- [ ] I2C 设备抽象
- [ ] PWM / 舵机控制
- [ ] 传感器插件框架
- [ ] 机器人技能框架
- [ ] ESP32 MQTT 桥接
- [ ] Raspberry Pi 3 / 4 / 5 验证矩阵

## 上游桌面 / 服务器安装

Hermes Agent IoT 主要用于 Raspberry Pi 与边缘部署。对于通用桌面或服务器用途，请安装上游 Hermes Agent。

### Windows（原生 PowerShell）

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

### Linux / macOS / WSL2

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

这些上游安装器不会安装此 fork 的 Pi2 专属 profiles 或 IoT 打包。

## 关于 Hermes Agent

Hermes Agent 是由 [Nous Research](https://nousresearch.com) 开发的自我进化 AI Agent。它提供终端界面、持久学习与记忆、定时自动化、subagents、多种执行后端、消息 gateway 以及对多种 LLM provider 的支持。

Hermes Agent IoT 不会取代上游项目。它将这一基础适配于 Raspberry Pi 2、ARMv7、低资源边缘节点、MQTT/Home Assistant 环境以及未来的机器人集成。

## 许可与署名

Hermes Agent IoT 衍生自 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)，遵循本仓库的 [MIT License](LICENSE)。在再分发衍生作品时请保留上游版权与署名。
