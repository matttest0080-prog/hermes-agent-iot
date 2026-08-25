<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent IoT" width="100%">
</p>

# Hermes Agent IoT

> Agente Hermes ligero para Raspberry Pi 2 / ARMv7, MQTT, Home Assistant, robótica e IA de borde de bajos recursos.

<p align="center">
  <a href="https://pypi.org/project/hermes-agent-iot/"><img src="https://img.shields.io/badge/PyPI-hermes--agent--iot-blue?style=for-the-badge" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Upstream-NousResearch%2Fhermes--agent-blueviolet?style=for-the-badge" alt="Upstream Hermes Agent"></a>
  <a href="README_PI2.md"><img src="https://img.shields.io/badge/Raspberry%20Pi%202-ARMv7-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white" alt="Raspberry Pi 2"></a>
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/Lang-English-lightgrey?style=for-the-badge" alt="English"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/Lang-اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
</p>

Hermes Agent IoT es un fork de [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) centrado en IoT y robótica. La rama mantenida `pi2-lite` se enfoca en despliegues restringidos de Raspberry Pi y edge, preservando el runtime y el ecosistema del Hermes Agent upstream.

## ¿Por qué Hermes Agent IoT?

- **Raspberry Pi 2 / ARMv7:** ruta de instalación de bajos recursos verificada para hardware de clase 1 GB.
- **Perfiles IoT:** perfiles de dependencias para MQTT, Home Assistant, MCP/ACP y RAG remoto (remote-first).
- **Despliegue edge-first:** mantén la inferencia pesada de IA en remoto mientras la Raspberry Pi maneja la orquestación del agente y la integración de dispositivos.
- **Dirección de robótica:** base para GPIO, I2C, PWM, sensores, actuadores y habilidades de robótica.
- **Consciente del upstream:** los cambios de compatibilidad IoT y ARMv7 se revisan por separado del rápido desarrollo upstream.

## Inicio rápido — Raspberry Pi 2

Hermes Agent IoT requiere Python `>=3.11,<3.14`. Instálalo en un entorno virtual:

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

> No uses pip del sistema, `sudo pip` ni `--break-system-packages`.

### Checkout del código fuente

Usa la rama mantenida `pi2-lite` cuando necesites los recursos completos del repositorio:

```bash
git clone --branch pi2-lite --depth 1 \
  https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
bash setup-pi2-minimal.sh --profile minimal
source ~/.hermes-venv/bin/activate
hermes setup model
hermes
```

> Conserva el directorio del clon. El instalador de código fuente usa una instalación editable de Python, por lo que mover o eliminar el checkout puede romper el entorno.

## Perfiles de instalación

| Perfil | Destino previsto |
| --- | --- |
| `minimal` | Línea base Raspberry Pi 2 / ARMv7 / 1 GB |
| `iot` | MQTT, Home Assistant, MCP/ACP e integraciones IoT relacionadas |
| `rag` | IoT más Honcho / RAG remoto (remote-first) |
| `full` | Raspberry Pi más potente, ARM64, servidor edge x86 o VM |
| `dev` | Sistemas de contribución y desarrollo |

Mantén alineados el extra de PyPI y el perfil de setup. Por ejemplo:

```bash
python -m pip install 'hermes-agent-iot[iot]==0.20.5.post2'
hermes-iot setup --profile iot
```

`full` y `dev` no se recomiendan para sistemas Raspberry Pi 2 / 1 GB.

## Estado del proyecto

| Capacidad | Estado |
| --- | --- |
| Instalación mínima Raspberry Pi 2 / ARMv7 | ✅ Verificado |
| Paquete PyPI público | ✅ Disponible |
| Perfil de dependencias mínimo | ✅ Disponible |
| Perfil de dependencias IoT | ✅ Disponible |
| Integración MQTT | ✅ Disponible |
| Integración Home Assistant | ✅ Disponible |
| RAG remoto (remote-first) | ✅ Disponible |
| Documentación de robótica | ✅ Disponible |
| Abstracción GPIO | 🛠 Hoja de ruta |
| Capa de dispositivos I2C | 🛠 Hoja de ruta |
| Control PWM / servos | 🛠 Hoja de ruta |
| Framework de plugins de sensores | 🛠 Hoja de ruta |
| Puente MQTT ESP32 | 🛠 Hoja de ruta |

## Documentación

- [Resumen del proyecto IoT](IOT_PROJECT.md) — objetivos, estado de soporte, perfiles y hoja de ruta.
- [Inicio rápido de Raspberry Pi 2](README_PI2.md) — matriz de dependencias, perfiles de configuración y guía de seguridad para Pi2.
- [Manual de Raspberry Pi 2](RASPBERRY_PI2_MANUAL.md) — documentación detallada de despliegue en Pi2.
- [Robótica](ROBOTICS.md) — notas de integración de robótica.
- [Política de seguridad](SECURITY.md) — reporte de vulnerabilidades y guía de seguridad.
- [Documentación del Hermes Agent upstream](https://hermes-agent.nousresearch.com/docs/) — características generales, proveedores, gateways, uso de escritorio/servidor e integraciones.

## Upstream vs Hermes Agent IoT

| Área | Hermes Agent upstream | Hermes Agent IoT |
| --- | --- | --- |
| Agente general de escritorio/servidor | Objetivo principal | Usa la base upstream |
| Raspberry Pi 2 / ARMv7 | No es objetivo principal | Objetivo principal de compatibilidad |
| Perfil mínimo de clase 1 GB | Modelo de dependencias general | Perfil `minimal` dedicado |
| Despliegue MQTT / Home Assistant | Integraciones generales | Perfil `iot` dedicado |
| Despliegue edge de bajos recursos | Runtime general | Foco principal del fork |
| Robótica | Alcance general del agente | Documentación y hoja de ruta orientadas a IoT/robótica |

Este fork puede quedarse intencionalmente atrás del `main` upstream mientras se revisan y validan los cambios de dependencias, los parches IoT y la compatibilidad ARMv7. Para un uso general de escritorio/servidor, prefiere el proyecto upstream.

## Versión verificada

Línea base verificada actual:

- PyPI: [`hermes-agent-iot 0.20.5.post2`](https://pypi.org/project/hermes-agent-iot/0.20.5.post2/)
- Tag: `iot-v0.20.5.post2`
- Python: `>=3.11,<3.14`
- Validación física: Raspberry Pi 2 Model B Rev 1.1, ARMv7 de 32 bits, 921 MiB RAM, Python 3.13.5

La línea base del wheel `minimal` se instaló en limpio y se sometió a smoke tests en hardware físico Raspberry Pi 2. Los extras opcionales más pesados requieren hardware acorde a su conjunto de dependencias.

## Actualizar una instalación de código fuente en Pi2

Mantén siempre las actualizaciones ancladas a la rama `pi2-lite`:

```bash
cd ~/hermes-agent-iot
source ~/.hermes-venv/bin/activate

git status --short
git switch pi2-lite
git fetch origin pi2-lite
git merge --ff-only origin/pi2-lite

bash setup-pi2-minimal.sh --profile minimal
```

Sustituye `minimal` por el perfil instalado originalmente. En el release IoT 0.20.4 y posteriores, un `hermes update` sin argumentos detecta la distribución `hermes-agent-iot` y usa `pi2-lite` por defecto; un `--branch pi2-lite` explícito sigue siendo útil en automatización para auditabilidad. Vuelve a ejecutar el instalador de perfil tras una actualización de código fuente.

## Hoja de ruta

- [x] Ruta de instalación Raspberry Pi 2 / ARMv7
- [x] Perfil de dependencias de bajos recursos
- [x] Perfil de dependencias IoT
- [x] Ruta de integración MQTT / Home Assistant
- [x] Paquete PyPI público
- [x] Validación física en Raspberry Pi 2
- [ ] Abstracción GPIO
- [ ] Abstracción de dispositivos I2C
- [ ] Control PWM / servos
- [ ] Framework de plugins de sensores
- [ ] Framework de habilidades de robótica
- [ ] Puente MQTT ESP32
- [ ] Matriz de validación Raspberry Pi 3 / 4 / 5

## Instalación de escritorio / servidor upstream

Hermes Agent IoT está orientado principalmente a Raspberry Pi y despliegues edge. Para uso general de escritorio o servidor, instala el Hermes Agent upstream.

### Windows (PowerShell nativo)

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

### Linux / macOS / WSL2

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

Estos instaladores upstream no instalan los perfiles específicos de Pi2 ni el empaquetado IoT de este fork.

## Acerca de Hermes Agent

Hermes Agent es el agente de IA con mejora continua desarrollado por [Nous Research](https://nousresearch.com). Ofrece una interfaz de terminal, aprendizaje y memoria persistentes, automatizaciones programadas, subagentes, múltiples backends de ejecución, gateways de mensajería y soporte para múltiples proveedores de LLM.

Hermes Agent IoT no reemplaza al proyecto upstream. Adapta esa base para Raspberry Pi 2, ARMv7, nodos edge de bajos recursos, entornos MQTT/Home Assistant e integraciones futuras de robótica.

## Licencia y atribución

Hermes Agent IoT deriva de [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) y sigue la [Licencia MIT](LICENSE) de este repositorio. Conserva el copyright y la atribución del upstream al redistribuir trabajos derivados.
