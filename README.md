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

## Why Hermes Agent IoT?

- **Raspberry Pi 2 / ARMv7:** verified low-resource installation path for 1 GB-class hardware.
- **IoT profiles:** dependency profiles for MQTT, Home Assistant, MCP/ACP, and remote-first RAG.
- **Edge-first deployment:** keep heavy AI inference remote while the Raspberry Pi handles agent orchestration and device integration.
- **Robotics direction:** foundation for GPIO, I2C, PWM, sensors, actuators, and robotics skills.
- **Upstream-aware:** IoT and ARMv7 compatibility changes are reviewed separately from fast-moving upstream development.

## Quick Start — Raspberry Pi 2

Hermes Agent IoT requires Python `>=3.11,<3.14`. Install it in a virtual environment:

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

> Do not use system pip, `sudo pip`, or `--break-system-packages`.

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
python -m pip install 'hermes-agent-iot[iot]==0.20.5.post2'
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

## Verified Release

Current verified baseline:

- PyPI: [`hermes-agent-iot 0.20.5.post2`](https://pypi.org/project/hermes-agent-iot/0.20.5.post2/)
- Tag: `iot-v0.20.5.post2`
- Python: `>=3.11,<3.14`
- Physical validation: Raspberry Pi 2 Model B Rev 1.1, 32-bit ARMv7, 921 MiB RAM, Python 3.13.5

The `minimal` wheel baseline was clean-installed and smoke-tested on physical Raspberry Pi 2 hardware. Heavier optional extras require hardware appropriate to their dependency set.

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

### Linux / macOS / WSL2

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

These upstream installers do not install this fork's Pi2-specific profiles or IoT packaging.

## About Hermes Agent

Hermes Agent is the self-improving AI agent developed by [Nous Research](https://nousresearch.com). It provides a terminal interface, persistent learning and memory, scheduled automations, subagents, multiple execution backends, messaging gateways, and support for multiple LLM providers.

Hermes Agent IoT does not replace the upstream project. It adapts that foundation for Raspberry Pi 2, ARMv7, low-resource edge nodes, MQTT/Home Assistant environments, and future robotics integrations.

## License and Attribution

Hermes Agent IoT is derived from [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) and follows this repository's [MIT License](LICENSE). Preserve upstream copyright and attribution when redistributing derived work.
