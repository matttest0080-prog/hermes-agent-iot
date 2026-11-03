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

#### 復原方式：依狀態擇一，不是已證實的根因修復

先保留原錯誤輸出，確認使用同一 venv／profile。若命令指向舊環境，可重新啟用新版並清除 shell 的命令快取；不需要先重裝：

```bash
source ~/.venvs/hermes-iot-0.22.5/bin/activate
hash -r
command -v hermes

hermes_cmd=(hermes)  # 僅適用於原本沒有 -p 的 default profile
# 若原指令有 -p，改用：hermes_cmd=(hermes -p your-original-profile)
# 保留原有 HERMES_HOME，不要重設到另一個 home。
"${hermes_cmd[@]}" gateway status --deep
```

1. **Gateway 確定未執行，且已安裝對應服務：** 啟動該服務，再查狀態。若 owner／profile 被拒絕，先核對 CLI 提示的實際 owner，不加 `--force` 或 `--all`。

   ```bash
   "${hermes_cmd[@]}" gateway start
   "${hermes_cmd[@]}" gateway status --deep
   ```

2. **Gateway 確定未執行，且沒有安裝服務：** 在另一個終端重做上述 venv／profile 選擇後，前景啟動 gateway；保留該終端，再回原終端重試原啟動指令。不要在已有 owner 時另開一個 gateway，也不要加 `--replace`。

   ```bash
   "${hermes_cmd[@]}" gateway run
   ```

3. **Gateway 已就緒但 CLI 仍失敗：** 先重試原指令一次，保留同一 profile 與錯誤輸出。若有 `HERMES_TUI_GATEWAY_URL`，核對是否為原本要連的目標；只在確認設定錯誤後更正，不盲目清除它以切換成本機 gateway。`status` 顯示執行中仍不等於 WebSocket／原 CLI 路徑已通過；持續失敗就繼續蒐集遮敏後的診斷，不反覆重啟。

4. **已確認 owner 異常且安排好維護窗口時，才考慮受控重啟：** 先保留紀錄，確認受影響工作均已結束；multiplexer 可能服務多個 profiles。在維護終端執行下列命令並尊重活動工作／owner 的拒絕提示，**不加 `--force`／`--all`**。手動 gateway 可能轉為前景執行，請保留該終端，另開終端以同一 venv／profile 查狀態與重試原指令。

   ```bash
   "${hermes_cmd[@]}" gateway restart
   ```

以上是環境校正、服務啟動與受控復原的操作指引，**並未在這次診斷中執行啟動／重啟，也不是對本次錯誤已驗證的修復**。若仍失敗，請附原啟動指令、`gateway status --deep` 與已遮敏的近期 gateway log；不要刪鎖檔、改用 local fallback 或忽略服務拒絕訊息。

### Pi 2B: Gateway connection failure (English; cause not confirmed)

The following error was reported on Pi 2B with `0.22.5.post3`:

```text
Error: Gateway connection failed; no local fallback
```

**The original failure has not been reproduced and its root cause is unconfirmed. No fix has been verified.** The user confirmed the active venv was `~/.venvs/hermes-iot-0.22.5`. Later read-only checks found the existing gateway `ready`, its local API TCP port reachable, and one WebSocket handshake successful. That only verifies that particular connection, not the original CLI command, selected profile, cold start, or long-lived connection. The diagnostic made no model requests, created no conversation sessions, and did not restart services or change configuration.

The message means the CLI did not complete its gateway connection and did not fall back to local execution. **It does not, by itself, prove that the gateway is stopped or the venv is broken.** Preserve the error before trying recovery; do not force a local fallback, delete PID/lock files, reinstall packages, or repeatedly restart services to bypass it.

Collect these read-only details:

```bash
printf 'VIRTUAL_ENV=%s\n' "${VIRTUAL_ENV:-<not activated>}"
command -v hermes
python -c 'import sys; from importlib.metadata import version; print(sys.executable); print(version("hermes-agent-iot"))'
```

Also provide the **exact failing launch command and error output**, including any `-p` profile arguments. Keep the same profile and `HERMES_HOME`; do not mix old and new venvs. If `HERMES_TUI_GATEWAY_URL` was configured, report whether it is set and a credential-redacted target. Never post `.env`, API keys, tokens, or credential-bearing URLs. A later successful handshake does not establish why the original command failed.

#### Conditional recovery, not a confirmed root-cause fix

Preserve the original error and profile selection first. If the command resolves to an old environment, reactivate the intended venv and clear the shell's command cache instead of reinstalling:

```bash
source ~/.venvs/hermes-iot-0.22.5/bin/activate
hash -r
command -v hermes

hermes_cmd=(hermes)  # Default profile ONLY if the original command had no -p.
# Otherwise use: hermes_cmd=(hermes -p your-original-profile)
# Preserve the original HERMES_HOME; do not redirect it to another home.
"${hermes_cmd[@]}" gateway status --deep
```

1. **Gateway confirmed stopped, with a matching service already installed:** Start that service and check status again. If ownership/profile checks refuse the operation, inspect the reported owner rather than adding `--force` or `--all`.

   ```bash
   "${hermes_cmd[@]}" gateway start
   "${hermes_cmd[@]}" gateway status --deep
   ```

2. **Gateway confirmed stopped, with no installed service or existing owner:** In another terminal, repeat the same venv/profile selection above, then run the gateway in the foreground. Keep that terminal open and retry the original launch command from the first terminal. Do not start a second owner or add `--replace`.

   ```bash
   "${hermes_cmd[@]}" gateway run
   ```

3. **Gateway ready, but the CLI still fails:** Retry the original command once, retaining the same profile and error output. If `HERMES_TUI_GATEWAY_URL` is set, verify that it names the intended target; correct it only after confirming a configuration mistake. Do not blindly unset it to switch to a local gateway. A running process/status is not proof that the WebSocket or original CLI path works. If the error persists, collect redacted diagnostics instead of restarting repeatedly.

4. **Owner confirmed unhealthy, with an agreed maintenance window:** Preserve logs and finish all affected work before a controlled restart. A multiplexer may serve several profiles. Run the following in a maintenance terminal, respect active-work/ownership refusals, and **do not add `--force` or `--all`**. A manually managed gateway may remain in the foreground; keep its terminal open and use another terminal with the same venv/profile to check status and retry the original command.

   ```bash
   "${hermes_cmd[@]}" gateway restart
   ```

These are environment correction, startup, and controlled-recovery instructions. **No startup/restart actions were performed during this diagnostic, and none is a verified repair for this incident.** If it persists, provide the exact launch command, `gateway status --deep` output, and recent credential-redacted gateway logs. Do not delete locks, enable a local fallback, or bypass service refusals.

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
