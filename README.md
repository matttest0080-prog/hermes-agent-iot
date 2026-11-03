<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent IoT" width="100%">
</p>

# Hermes Agent IoT

> Lightweight Hermes Agent for Raspberry Pi 2 / ARMv7, MQTT, Home Assistant, robotics, and low-resource edge AI.

<p align="center">
  <a href="https://pypi.org/project/hermes-agent-iot/"><img src="https://img.shields.io/badge/PyPI-hermes--agent--iot-blue?style=for-the-badge" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Upstream-NousResearch%2Fhermes--agent-blueviolet?style=for-the-badge" alt="Upstream Hermes Agent"></a>
  <a href="README_PI2.md"><img src="https://img.shields.io/badge/Raspberry%20Pi%202-ARMv7-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white" alt="Raspberry Pi 2"></a>
</p>

Hermes Agent IoT is an IoT/robotics-focused fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent). The maintained `pi2-lite` branch focuses on constrained Raspberry Pi and edge deployments while preserving the upstream Hermes Agent runtime and ecosystem.

> **版本與升級注意事項：** [`0.22.5.post3` 已正式發布 PyPI](https://pypi.org/project/hermes-agent-iot/0.22.5.post3/)，使用保留 MIT 署名的獨立 `browser-harness-hermes-compat` 與 Pillow 13 修補；[正式產物與驗收紀錄](docs/release-v0.22.5.post3.md)已核對真正 tag CI／匿名 PyPI bytes。舊 `0.22.2.post1` 不含這輪安全修補。升級建議使用**全新 venv**，不要混裝官方／獨立 browser distributions；見 [相容性與遷移說明](docs/browser-harness-compat.md) 及 [同步驗證紀錄](docs/upstream-review-v0.22.5.md)。

## 相關影片

- [YouTube Shorts](https://www.youtube.com/shorts/8Nqv4ri6gH8)

## Why Hermes Agent IoT?

- **Raspberry Pi 2 / ARMv7:** verified low-resource installation path for 1 GB-class hardware.
- **IoT profiles:** dependency profiles for MQTT, Home Assistant, MCP/ACP, and remote-first RAG.
- **Edge-first deployment:** keep heavy AI inference remote while the Raspberry Pi handles agent orchestration and device integration.
- **Robotics direction:** foundation for GPIO, I2C, PWM, sensors, actuators, and robotics skills.
- **Upstream-aware:** IoT and ARMv7 compatibility changes are reviewed separately from fast-moving upstream development.

## Quick Start — Raspberry Pi 2

Hermes Agent IoT requires Python `>=3.11,<3.15`. Install it in a virtual environment:

```bash
python3 --version
python3 -m venv ~/.venvs/hermes-iot-0.22.5
source ~/.venvs/hermes-iot-0.22.5/bin/activate
python -m pip install --upgrade pip
python -m pip install 'hermes-agent-iot[minimal]==0.22.5.post3'
python -m pip check

hermes-iot setup --profile minimal
hermes-iot profile show
hermes setup model
hermes
```

> Do not use system pip, `sudo pip`, or `--break-system-packages`.

### Pi 2B 已回報：Gateway 連線失敗（原因待確認）

在 `0.22.5.post3` 的 Pi 2B 環境曾回報：

```text
Error: Gateway connection failed; no local fallback
```

**目前尚未重現原錯誤、根因未確認，不能視為已修復。** 使用者已確認啟用 `~/.venvs/hermes-iot-0.22.5`。後續唯讀診斷中，既有 gateway 回報 `ready`，本機 API TCP 可連，且一次 WebSocket 握手成功；這只代表當次連線，不等於原 CLI 啟動流程、指定 profile、冷啟動或長期連線已驗收。診斷沒有送模型請求、建立對話、重啟服務或修改設定。

此訊息表示 CLI 未完成 gateway 連線流程，且沒有轉為 local fallback；**不能僅憑訊息判定 gateway 未啟動或 venv 損壞**。先保留錯誤現場，不要為繞過錯誤強制 fallback、刪除 PID／lock 檔、重裝套件或反覆重啟服務。

回報時請提供：

```bash
printf 'VIRTUAL_ENV=%s\n' "${VIRTUAL_ENV:-<not activated>}"
command -v hermes
python -c 'import sys; from importlib.metadata import version; print(sys.executable); print(version("hermes-agent-iot"))'
```

另附**實際觸發錯誤的完整啟動指令與錯誤輸出**；若有 `-p` 等 profile 參數，請保留同一 profile 排查，不要任意切換 `HERMES_HOME` 或混用新舊 venv。若設定過 `HERMES_TUI_GATEWAY_URL`，只回報是否設定及已遮蔽憑證的目標；請勿貼出 `.env`、API key、token 或含憑證的 URL。單次握手成功不能取代原指令的重現與根因分析。

### Source checkout

Use the maintained `pi2-lite` branch when you need the complete repository assets:

```bash
git clone --branch pi2-lite --depth 1 \
  https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
bash setup-pi2-minimal.sh --profile minimal
source ~/.hermes-venv/bin/activate
hermes setup model
hermes
```

> Keep the clone directory. The source installer uses an editable Python installation, so moving or deleting the checkout can break the environment.

## Install Profiles

| Profile | Intended target |
| --- | --- |
| `minimal` | Raspberry Pi 2 / ARMv7 / 1 GB baseline |
| `iot` | MQTT, Home Assistant, MCP/ACP and related IoT integrations |
| `rag` | IoT plus Honcho / remote-first RAG |
| `full` | Stronger Raspberry Pi, ARM64, x86 edge server or VM |
| `dev` | Contributor and development systems |

Keep the PyPI extra and setup profile aligned. For example:

```bash
python -m pip install 'hermes-agent-iot[iot]==0.22.5.post3'
hermes-iot setup --profile iot
```

`full` and `dev` are not recommended for Raspberry Pi 2 / 1 GB systems.

## Project Status

| Capability | Status |
| --- | --- |
| Raspberry Pi 2 / ARMv7 minimal install | ✅ Verified |
| Public PyPI package | ✅ Available |
| Minimal dependency profile | ✅ Available |
| IoT dependency profile | ✅ Available |
| MQTT integration | ✅ Available |
| Home Assistant integration | ✅ Available |
| Remote-first RAG | ✅ Available |
| Robotics documentation | ✅ Available |
| GPIO abstraction | 🛠 Roadmap |
| I2C device layer | 🛠 Roadmap |
| PWM / servo control | 🛠 Roadmap |
| Sensor plugin framework | 🛠 Roadmap |
| ESP32 MQTT bridge | 🛠 Roadmap |

## Documentation

- [IoT Project Overview](IOT_PROJECT.md) — project goals, support status, profiles, and roadmap.
- [Raspberry Pi 2 Quick Start](README_PI2.md) — dependency matrix, configuration profiles, and Pi2 safety guidance.
- [Raspberry Pi 2 Manual](RASPBERRY_PI2_MANUAL.md) — detailed Pi2 deployment documentation.
- [Robotics](ROBOTICS.md) — robotics integration notes.
- [Security Policy](SECURITY.md) — vulnerability reporting and security guidance.
- [Upstream Hermes Agent documentation](https://hermes-agent.nousresearch.com/docs/) — general Hermes Agent features, providers, gateways, desktop/server usage, and integrations.

## Upstream vs Hermes Agent IoT

| Area | Upstream Hermes Agent | Hermes Agent IoT |
| --- | --- | --- |
| General desktop/server agent | Primary target | Uses upstream foundation |
| Raspberry Pi 2 / ARMv7 | Not primary target | Primary compatibility target |
| 1 GB-class minimal profile | General dependency model | Dedicated `minimal` profile |
| MQTT / Home Assistant deployment | General integrations | Dedicated `iot` profile |
| Low-resource edge deployment | General runtime | Primary fork focus |
| Robotics | General agent scope | IoT/robotics-oriented documentation and roadmap |

This fork may intentionally lag upstream `main` while dependency changes, IoT patches, and ARMv7 compatibility are reviewed and validated. For general desktop/server Hermes Agent usage, prefer the upstream project.

## 發行與驗證紀錄

- 本版 package／tag 識別：`hermes-agent-iot 0.22.5.post3`／`iot-v0.22.5.post3`。
- [PyPI 對應版本與正式檔案雜湊](https://pypi.org/project/hermes-agent-iot/0.22.5.post3/#files)／[GitHub release 與 tag](https://github.com/matttest0080-prog/hermes-agent-iot/releases/tag/iot-v0.22.5.post3)。正式 wheel SHA256：`46ae064a902296cb744a16ead141cf4707456b38b8a93d98f510da07b738422a`；[發布與驗收範圍](docs/release-v0.22.5.post3.md)。
- Pi 2B 正式 registry 實測：Rev 1.1、ARMv7、921 MiB RAM、Python 3.13.5；**本版正式 wheel** 在新隔離目錄完成五 profiles hash dry-run、正常 minimal 安裝與 `pip check`、10 項 smoke、12 項 SQLite deadline／逐 byte回滾控制，整體 exit 0，installed bytes 匹配正式 PyPI wheel。**實際只安裝 minimal**；localhost fixture 不是實際模型、MQTT／HA／GPIO／CDP 或長期負載驗收，未修改既有服務。
- 從舊版升級請使用前述新 venv，保留舊環境與服務供回復。`pip install --upgrade` 不一定移除舊 orphan `browser-harness`，混裝會造成 Pillow 要求衝突或同名模組互相覆寫。

### 歷史已發布驗證：0.22.2.post1

以下保留舊版 receipt，**不是 0.22.5.post3 的 artifact 或安全驗證**：

- PyPI: [`hermes-agent-iot 0.22.2.post1`](https://pypi.org/project/hermes-agent-iot/0.22.2.post1/)
- Tag: `iot-v0.22.2.post1`
- Commit: `2c08f4ec97445d8f26ab5c35515b2f94652aaddf`
- Wheel: `hermes_agent_iot-0.22.2.post1-py3-none-any.whl`
- Wheel SHA-256: `e46b7049940f14928d0dd014f44494126faca261363e9240fa700fb84d13fd8f`
- Workflow: https://github.com/matttest0080-prog/hermes-agent-iot/actions/runs/39356318990
- Python: `>=3.11,<3.15`
- Physical validation: Raspberry Pi 2 Model B Rev 1.1, 32-bit ARMv7, 921 MiB RAM, Python 3.13.5

The `minimal` wheel baseline was clean-installed from public PyPI on physical Raspberry Pi 2 hardware on 2026-10-20: `pip check` clean, `hermes --version` = 0.22.2.post1, wheel SHA-256 matched, and a one-shot agent turn returned `PI2-OK` in 81.6 s using a remote model over SSH. That verifies the Pi 2 client/runtime path, not local inference on the Pi. Heavier optional extras require hardware appropriate to their dependency set.

## Updating a Pi2 Source Installation

Always keep updates pinned to the `pi2-lite` branch:

```bash
cd ~/hermes-agent-iot
source ~/.hermes-venv/bin/activate

git status --short
git switch pi2-lite
git fetch origin pi2-lite
git merge --ff-only origin/pi2-lite

bash setup-pi2-minimal.sh --profile minimal
```

Replace `minimal` with the profile originally installed. In IoT release 0.20.4
and later, a bare `hermes update` detects the `hermes-agent-iot` distribution
and defaults to `pi2-lite`; an explicit `--branch pi2-lite` remains useful in
automation for auditability. Rerun the profile installer after a source update.

## Roadmap

- [x] Raspberry Pi 2 / ARMv7 installation path
- [x] Low-resource dependency profile
- [x] IoT dependency profile
- [x] MQTT / Home Assistant integration path
- [x] Public PyPI package
- [x] Physical Raspberry Pi 2 validation
- [ ] GPIO abstraction
- [ ] I2C device abstraction
- [ ] PWM / servo control
- [ ] Sensor plugin framework
- [ ] Robotics skill framework
- [ ] ESP32 MQTT bridge
- [ ] Raspberry Pi 3 / 4 / 5 validation matrix

## Upstream Desktop / Server Installation

Hermes Agent IoT is primarily for Raspberry Pi and edge deployments. For general desktop or server use, install the upstream Hermes Agent.

### Windows (native PowerShell)

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

The source installer delegates Python 3.14, Node.js, npm, ripgrep, FFmpeg,
and Python dependencies to PM. If Git is absent, it stages the verified Git
for Windows archive in Hermes' tool store. It does not replace your system Git.
See [installation methods](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
for the separate MSIX/App Installer package and its update ownership.

### Linux / macOS / WSL2

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

> **Android / Termux:** A signed APT repository is available for aarch64 devices, with a `stable` channel (tagged releases) and a prerelease `canary` channel. The package includes Python, Node.js, and the TUI. Use the [Termux guide](https://hermes-agent.nousresearch.com/docs/getting-started/termux), not the desktop/server installer script.

These upstream installers do not install this fork's Pi2-specific profiles or IoT packaging.

## About Hermes Agent

Hermes Agent is the self-improving AI agent developed by [Nous Research](https://nousresearch.com). It provides a terminal interface, persistent learning and memory, scheduled automations, subagents, multiple execution backends, messaging gateways, and support for multiple LLM providers.

Hermes Agent IoT does not replace the upstream project. It adapts that foundation for Raspberry Pi 2, ARMv7, low-resource edge nodes, MQTT/Home Assistant environments, and future robotics integrations.

## License and Attribution

Hermes Agent IoT is derived from [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) and follows this repository's [MIT License](LICENSE). Preserve upstream copyright and attribution when redistributing derived work.
