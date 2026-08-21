# Hermes Agent IoT

Hermes Agent IoT is a low-resource IoT and robotics fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent), focused on Raspberry Pi, ARMv7, MQTT, Home Assistant, and edge-agent deployments.

## Project goals

- Run a practical Hermes Agent baseline on Raspberry Pi 2 / ARMv7 / 1 GB-class systems.
- Provide lightweight install profiles for constrained edge devices.
- Connect AI-agent workflows to MQTT and Home Assistant environments.
- Provide a foundation for sensors, actuators, robotics, and remote-first AI workloads.
- Preserve a clear relationship with upstream Hermes Agent while documenting IoT-specific behavior separately.

## Current status

| Capability | Status |
| --- | --- |
| Raspberry Pi 2 / ARMv7 minimal install | Verified |
| Public PyPI package | Available |
| `minimal` install profile | Available |
| `iot` install profile | Available |
| MQTT integration | Available in IoT profile |
| Home Assistant integration | Available in IoT profile |
| Remote-first RAG profile | Available |
| Robotics documentation | Available |
| GPIO abstraction layer | Roadmap |
| I2C device layer | Roadmap |
| PWM / servo control | Roadmap |
| Sensor plugin framework | Roadmap |
| ESP32 MQTT bridge | Roadmap |

## Quick start: Raspberry Pi 2

Hermes Agent IoT requires Python `>=3.11,<3.14`. Use a virtual environment.

```bash
python3 -m venv ~/.venvs/hermes-iot
source ~/.venvs/hermes-iot/bin/activate
python -m pip install --upgrade pip
python -m pip install 'hermes-agent-iot[minimal]==0.20.4.post1'
python -m pip check

hermes-iot setup --profile minimal
hermes setup model
hermes
```

Do not use system pip, `sudo pip`, or `--break-system-packages` for this installation.

## Source installation

Use the maintained `pi2-lite` branch for complete repository assets:

```bash
git clone --branch pi2-lite --depth 1 \
  https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
bash setup-pi2-minimal.sh --profile minimal
source ~/.hermes-venv/bin/activate
hermes setup model
hermes
```

## Install profiles

| Profile | Intended use |
| --- | --- |
| `minimal` | Raspberry Pi 2 / ARMv7 / 1 GB baseline |
| `iot` | MQTT, Home Assistant, MCP/ACP and related IoT integrations |
| `rag` | IoT plus remote-first RAG / Honcho integration |
| `full` | Stronger Raspberry Pi, ARM64, x86 edge server or VM |
| `dev` | Contributor and development environments |

## Documentation

- [Main README](README.md) — complete Hermes Agent and fork installation documentation.
- [Raspberry Pi 2 Quick Start](README_PI2.md) — dependency matrix, profiles, and Pi2 guidance.
- [Raspberry Pi 2 Manual](RASPBERRY_PI2_MANUAL.md) — detailed Pi2 deployment documentation.
- [Robotics](ROBOTICS.md) — robotics integration notes.
- [Security Policy](SECURITY.md) — vulnerability reporting and security guidance.

## Upstream relationship

This repository is based on NousResearch/Hermes Agent. The `pi2-lite` branch may intentionally lag upstream while dependency changes, IoT patches, and ARMv7 compatibility are reviewed and validated.

For general desktop/server Hermes Agent usage, refer to the upstream project. For Raspberry Pi 2, low-resource edge nodes, MQTT, Home Assistant, and IoT/robotics-oriented deployment, use the documentation in this repository.

## Roadmap

- [x] Raspberry Pi 2 / ARMv7 installation path
- [x] Low-resource dependency profile
- [x] IoT dependency profile
- [x] MQTT / Home Assistant integration path
- [x] Public PyPI wheel
- [x] Raspberry Pi 2 hardware validation
- [ ] GPIO abstraction
- [ ] I2C device abstraction
- [ ] PWM / servo control
- [ ] Sensor plugin framework
- [ ] Robotics skill framework
- [ ] ESP32 MQTT bridge
- [ ] Raspberry Pi 3 / 4 / 5 validation matrix

## License

This fork follows the repository's [MIT License](LICENSE). Preserve upstream copyright and attribution when redistributing derived work.
