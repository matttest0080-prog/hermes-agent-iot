# Hermes Agent IoT

> Lightweight Hermes Agent for Raspberry Pi 2 / ARMv7, MQTT, Home Assistant, robotics, and low-resource edge AI.

Hermes Agent IoT is an IoT/robotics-focused fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent). The maintained `pi2-lite` branch focuses on constrained Raspberry Pi and edge deployments while preserving the upstream Hermes Agent runtime and ecosystem.

## Why this fork?

- **Raspberry Pi 2 / ARMv7:** verified low-resource installation path for 1 GB-class hardware.
- **IoT profiles:** dependency profiles for MQTT, Home Assistant, MCP/ACP, and remote-first RAG.
- **Edge-first deployment:** keep heavy AI inference remote while the Raspberry Pi handles agent orchestration and device integration.
- **Robotics direction:** foundation for GPIO, I2C, PWM, sensors, actuators, and robotics skills.
- **Upstream-aware:** IoT and ARMv7 compatibility changes are reviewed separately from fast-moving upstream development.

## Quick Start — Raspberry Pi 2

Hermes Agent IoT requires Python `>=3.11,<3.14`. Install it in a virtual environment:

```bash
python3 -m venv ~/.venvs/hermes-iot
source ~/.venvs/hermes-iot/bin/activate
python -m pip install --upgrade pip
python -m pip install 'hermes-agent-iot[minimal]==0.20.0.post2'
python -m pip check

hermes-iot setup --profile minimal
hermes setup model
hermes
```

Do not use system pip, `sudo pip`, or `--break-system-packages`.

### Source checkout

```bash
git clone --branch pi2-lite --depth 1 \
  https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
bash setup-pi2-minimal.sh --profile minimal
source ~/.hermes-venv/bin/activate
hermes setup model
hermes
```

## Install Profiles

| Profile | Target |
| --- | --- |
| `minimal` | Raspberry Pi 2 / ARMv7 / 1 GB baseline |
| `iot` | MQTT, Home Assistant, MCP/ACP and IoT integrations |
| `rag` | IoT plus Honcho / remote-first RAG |
| `full` | Stronger Raspberry Pi, ARM64, x86 edge server or VM |
| `dev` | Contributor and development systems |

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

- [Complete README](README.md) — detailed Pi2 release, install/update instructions, and upstream Hermes documentation.
- [IoT Project Overview](IOT_PROJECT.md) — goals, status, profiles, and roadmap.
- [Raspberry Pi 2 Quick Start](README_PI2.md) — Pi2 dependency matrix and safety guidance.
- [Raspberry Pi 2 Manual](RASPBERRY_PI2_MANUAL.md) — detailed deployment manual.
- [Robotics](ROBOTICS.md) — robotics integration notes.
- [Security Policy](SECURITY.md) — security and vulnerability reporting.

## Upstream vs Hermes Agent IoT

| Area | Upstream Hermes Agent | Hermes Agent IoT |
| --- | --- | --- |
| General desktop/server agent | Primary target | Supported through upstream foundation |
| Raspberry Pi 2 / ARMv7 | Not primary target | Primary compatibility target |
| 1 GB-class minimal profile | Not IoT-specific | `minimal` profile |
| MQTT / Home Assistant deployment | General integrations | Dedicated `iot` profile |
| Low-resource edge deployment | General runtime | Primary fork focus |
| Robotics documentation | General agent scope | IoT/robotics-specific guidance |

## Release

Current verified baseline: `hermes-agent-iot 0.20.0.post2`, tag `iot-v0.20.0.post2`.

For release provenance, wheel hash, physical Raspberry Pi 2 validation, update procedures, and full upstream documentation, see the [complete README](README.md).

## Roadmap

- [x] Raspberry Pi 2 / ARMv7 installation path
- [x] Minimal and IoT dependency profiles
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

## License and attribution

Hermes Agent IoT is derived from [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) and follows this repository's [MIT License](LICENSE). Upstream attribution and copyright notices must be preserved.
