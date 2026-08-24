"""MQTT tools for lightweight IoT sensor and device control.

The MQTT integration is intentionally small and Pi-friendly. It uses paho-mqtt
only when a tool is called, and reads broker settings from environment vars:

- MQTT_HOST: broker hostname/IP (required for tool availability)
- MQTT_PORT: broker port (default: 1883)
- MQTT_USERNAME / MQTT_PASSWORD: optional credentials
- MQTT_CLIENT_ID: optional client ID prefix
- MQTT_TLS: true/1/yes/on to enable TLS
- MQTT_ALLOW_INSECURE_CREDENTIALS: explicit opt-in for credentials without TLS

Tools:
- mqtt_publish: publish a payload to a command/sensor topic
- mqtt_subscribe_recent: listen briefly for retained/recent sensor messages
- mqtt_device_command: publish a command and optionally wait for state messages
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
import secrets
import threading
import time
from typing import Any, Callable

from tools.registry import registry, tool_error


_MAX_TOPIC_BYTES = 65535
_MAX_PAYLOAD_BYTES = 256 * 1024
_MAX_INBOUND_PAYLOAD_BYTES = 64 * 1024
_MAX_INBOUND_RESPONSE_BYTES = 256 * 1024


def _mqtt_client_factory():
    try:
        from tools.lazy_deps import ensure

        ensure("tool.mqtt", prompt=False)
    except Exception:
        # If lazy install is unavailable/disabled, fall through to the import so
        # the handler reports the concrete ModuleNotFoundError to the caller.
        pass

    import paho.mqtt.client as mqtt  # type: ignore[unresolved-import]

    return mqtt.Client


@dataclass(frozen=True)
class MQTTConfig:
    host: str
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = ""
    tls: bool = False
    allow_insecure_credentials: bool = False


def _parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_config() -> MQTTConfig:
    host = os.getenv("MQTT_HOST", "").strip()
    port_raw = os.getenv("MQTT_PORT", "1883").strip() or "1883"
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError(f"MQTT_PORT must be an integer, got {port_raw!r}") from exc
    if port <= 0 or port > 65535:
        raise ValueError(f"MQTT_PORT must be between 1 and 65535, got {port}")
    return MQTTConfig(
        host=host,
        port=port,
        username=os.getenv("MQTT_USERNAME", "").strip(),
        password=os.getenv("MQTT_PASSWORD", ""),
        client_id=os.getenv("MQTT_CLIENT_ID", "").strip(),
        tls=_parse_bool(os.getenv("MQTT_TLS")),
        allow_insecure_credentials=_parse_bool(os.getenv("MQTT_ALLOW_INSECURE_CREDENTIALS")),
    )


def _check_mqtt_available() -> bool:
    """Show MQTT tools only when a broker host is configured."""
    return bool(os.getenv("MQTT_HOST", "").strip())


def _validate_topic(topic: str, *, allow_wildcards: bool) -> str:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("MQTT topic must not be empty")
    if len(topic.encode("utf-8")) > _MAX_TOPIC_BYTES:
        raise ValueError("MQTT topic exceeds 65535 bytes")
    if "\x00" in topic:
        raise ValueError("MQTT topic must not contain NUL bytes")
    if not allow_wildcards and ("+" in topic or "#" in topic):
        raise ValueError("MQTT publish/command topics cannot contain wildcards '+' or '#'")
    if allow_wildcards:
        parts = topic.split("/")
        for i, part in enumerate(parts):
            if "#" in part and not (part == "#" and i == len(parts) - 1):
                raise ValueError("MQTT multi-level wildcard '#' must occupy the final topic level")
            if "+" in part and part != "+":
                raise ValueError("MQTT single-level wildcard '+' must occupy a whole topic level")
    return topic


def _payload_to_text(payload: Any) -> str:
    if isinstance(payload, str):
        text = payload
    elif isinstance(payload, (dict, list, int, float, bool)) or payload is None:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    else:
        text = str(payload)
    if len(text.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise ValueError("MQTT payload exceeds 256 KiB safety limit")
    return text


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int, name: str) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
        raise ValueError(f"{name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def _bounded_float(value: Any, *, default: float, minimum: float, maximum: float, name: str) -> float:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(parsed) or parsed < minimum or parsed > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def _strict_bool(value: Any, *, default: bool, name: str) -> bool:
    if value is None or type(value) is not bool:
        raise ValueError(f"{name} must be a boolean")
    return value


def _make_client(config: MQTTConfig):
    client_cls = _mqtt_client_factory()
    prefix = config.client_id or "hermes-iot"
    client_id = f"{prefix}-{os.getpid()}-{secrets.token_hex(8)}"
    client = client_cls(client_id=client_id)
    if config.username:
        client.username_pw_set(config.username, config.password or None)
    if config.tls:
        client.tls_set()
    return client


def _connect_client(config: MQTTConfig):
    if not config.host:
        raise ValueError("MQTT_HOST is required")
    if config.password and not config.username:
        raise ValueError("MQTT_PASSWORD requires MQTT_USERNAME")
    if (config.username or config.password) and not config.tls and not config.allow_insecure_credentials:
        raise ValueError(
            "MQTT credentials require MQTT_TLS=true; set "
            "MQTT_ALLOW_INSECURE_CREDENTIALS=true only for trusted plaintext networks"
        )
    client = _make_client(config)
    try:
        client.connect(config.host, config.port, keepalive=60)
    except Exception:
        _safe_close_client(client)
        raise
    return client


def _safe_close_client(client: Any) -> None:
    """Best-effort cleanup that never masks the primary MQTT error."""
    try:
        client.loop_stop()
    except Exception:
        pass
    try:
        client.disconnect()
    except Exception:
        pass


def _inbound_payload_size(msg: Any) -> int:
    raw_payload = getattr(msg, "payload", b"")
    if isinstance(raw_payload, (bytes, bytearray, memoryview)):
        return len(raw_payload)
    return len(str(raw_payload).encode("utf-8"))


def _inbound_topic_size(msg: Any) -> int:
    topic = getattr(msg, "topic", "")
    if isinstance(topic, str):
        return len(topic.encode("utf-8"))
    return len(str(topic).encode("utf-8"))


def _message_to_dict(msg: Any) -> dict[str, Any]:
    raw_payload = getattr(msg, "payload", b"")
    if _inbound_payload_size(msg) > _MAX_INBOUND_PAYLOAD_BYTES:
        raise ValueError("MQTT inbound payload exceeds per-message safety limit")
    if isinstance(raw_payload, bytes):
        payload = raw_payload.decode("utf-8", errors="replace")
    else:
        payload = str(raw_payload)
    return {
        "topic": getattr(msg, "topic", ""),
        "payload": payload,
        "qos": int(getattr(msg, "qos", 0) or 0),
        "retain": bool(getattr(msg, "retain", False)),
        "received_at": datetime.now(timezone.utc).isoformat(),
    }


def _serialized_message_size(message: dict[str, Any]) -> int:
    return len(
        json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


def _publish(topic: str, payload: str, *, qos: int, retain: bool) -> dict[str, Any]:
    config = _get_config()
    client = _connect_client(config)
    try:
        client.loop_start()
        result = client.publish(topic, payload, qos=qos, retain=retain)
        if hasattr(result, "wait_for_publish"):
            result.wait_for_publish(timeout=10)
        if getattr(result, "rc", 0) not in (0, None):
            raise RuntimeError(f"MQTT publish failed with rc={result.rc}")
        if hasattr(result, "is_published") and not result.is_published():
            raise RuntimeError("MQTT publish did not complete before timeout")
        return {"success": True, "topic": topic, "qos": qos, "retain": retain, "bytes": len(payload.encode("utf-8"))}
    finally:
        _safe_close_client(client)


def _subscription_rejection(reason_codes: Any) -> str | None:
    """Return an error for MQTT 3 granted-QoS 128 or MQTT 5 failure codes."""
    codes = reason_codes if isinstance(reason_codes, (list, tuple)) else [reason_codes]
    for code in codes:
        if code is None:
            continue
        if getattr(code, "is_failure", False) is True:
            return str(code)
        value = getattr(code, "value", code)
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            continue
        if numeric >= 128:
            return str(code)
    return None


def _subscribe_recent(topic_filter: str, *, timeout_seconds: float, max_messages: int, qos: int = 0) -> dict[str, Any]:
    config = _get_config()
    messages: deque[dict[str, Any]] = deque(maxlen=max_messages)
    accepted_bytes = 0
    dropped_messages = 0
    dropped_bytes = 0
    client = _connect_client(config)
    subscribed = threading.Event()
    subscribe_errors: list[str] = []

    def on_message(client_obj, userdata, msg):  # noqa: ANN001 - paho callback signature
        nonlocal accepted_bytes, dropped_messages, dropped_bytes
        payload_bytes = _inbound_payload_size(msg)
        if payload_bytes > _MAX_INBOUND_PAYLOAD_BYTES:
            dropped_messages += 1
            dropped_bytes += payload_bytes
            return
        controlled_bytes = payload_bytes + _inbound_topic_size(msg)
        if accepted_bytes + controlled_bytes > _MAX_INBOUND_RESPONSE_BYTES:
            dropped_messages += 1
            dropped_bytes += payload_bytes
            return
        message = _message_to_dict(msg)
        message_bytes = _serialized_message_size(message)
        if accepted_bytes + message_bytes > _MAX_INBOUND_RESPONSE_BYTES:
            dropped_messages += 1
            dropped_bytes += payload_bytes
            return
        messages.append(message)
        accepted_bytes += message_bytes

    def on_connect(client_obj, userdata, flags, reason_code, properties=None):  # noqa: ANN001
        rc = getattr(reason_code, "value", reason_code)
        if rc not in (0, None):
            subscribe_errors.append(f"MQTT connect failed with rc={rc}")
            subscribed.set()
            return
        result = client_obj.subscribe(topic_filter, qos=qos)
        sub_rc = result[0] if isinstance(result, tuple) else getattr(result, "rc", 0)
        if sub_rc not in (0, None):
            subscribe_errors.append(f"MQTT subscribe failed with rc={sub_rc}")
            subscribed.set()

    def on_subscribe(client_obj, userdata, mid, reason_codes, properties=None):  # noqa: ANN001
        rejection = _subscription_rejection(reason_codes)
        if rejection is not None:
            subscribe_errors.append(f"MQTT subscription rejected: {rejection}")
        subscribed.set()

    client.on_message = on_message
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    try:
        client.loop_start()
        if not subscribed.wait(timeout=10):
            raise RuntimeError("MQTT subscribe acknowledgement timed out")
        if subscribe_errors:
            raise RuntimeError(subscribe_errors[0])
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline and len(messages) < max_messages:
            time.sleep(0.05)
        result = {
            "success": True,
            "topic_filter": topic_filter,
            "count": len(messages),
            "messages": list(messages),
            "dropped_messages": dropped_messages,
            "dropped_bytes": dropped_bytes,
            "note": "MQTT brokers only return retained messages or messages published while this tool is listening.",
        }
        if dropped_messages:
            result["warning"] = "One or more MQTT messages were dropped by inbound payload safety limits."
        return result
    finally:
        _safe_close_client(client)


def _command_and_wait(
    command_topic: str,
    payload: str,
    *,
    state_topic_filter: str,
    timeout_seconds: float,
    qos: int,
    retain: bool,
) -> dict[str, Any]:
    """Subscribe to state first, then publish a command on the same client."""
    config = _get_config()
    client = _connect_client(config)
    messages: deque[dict[str, Any]] = deque(maxlen=10)
    accepted_bytes = 0
    dropped_messages = 0
    dropped_bytes = 0
    subscribed = threading.Event()
    subscribe_errors: list[str] = []

    def on_message(client_obj, userdata, msg):  # noqa: ANN001
        nonlocal accepted_bytes, dropped_messages, dropped_bytes
        payload_bytes = _inbound_payload_size(msg)
        if payload_bytes > _MAX_INBOUND_PAYLOAD_BYTES:
            dropped_messages += 1
            dropped_bytes += payload_bytes
            return
        controlled_bytes = payload_bytes + _inbound_topic_size(msg)
        if accepted_bytes + controlled_bytes > _MAX_INBOUND_RESPONSE_BYTES:
            dropped_messages += 1
            dropped_bytes += payload_bytes
            return
        message = _message_to_dict(msg)
        message_bytes = _serialized_message_size(message)
        if accepted_bytes + message_bytes > _MAX_INBOUND_RESPONSE_BYTES:
            dropped_messages += 1
            dropped_bytes += payload_bytes
            return
        messages.append(message)
        accepted_bytes += message_bytes

    def on_connect(client_obj, userdata, flags, reason_code, properties=None):  # noqa: ANN001
        rc = getattr(reason_code, "value", reason_code)
        if rc not in (0, None):
            subscribe_errors.append(f"MQTT connect failed with rc={rc}")
            subscribed.set()
            return
        result = client_obj.subscribe(state_topic_filter, qos=0)
        sub_rc = result[0] if isinstance(result, tuple) else getattr(result, "rc", 0)
        if sub_rc not in (0, None):
            subscribe_errors.append(f"MQTT subscribe failed with rc={sub_rc}")
            subscribed.set()

    def on_subscribe(client_obj, userdata, mid, reason_codes, properties=None):  # noqa: ANN001
        rejection = _subscription_rejection(reason_codes)
        if rejection is not None:
            subscribe_errors.append(f"MQTT state subscription rejected: {rejection}")
        subscribed.set()

    client.on_message = on_message
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    try:
        client.loop_start()
        if not subscribed.wait(timeout=10):
            raise RuntimeError("MQTT state subscription acknowledgement timed out")
        if subscribe_errors:
            raise RuntimeError(subscribe_errors[0])

        publish_result = client.publish(command_topic, payload, qos=qos, retain=retain)
        if hasattr(publish_result, "wait_for_publish"):
            publish_result.wait_for_publish(timeout=10)
        if getattr(publish_result, "rc", 0) not in (0, None):
            raise RuntimeError(f"MQTT publish failed with rc={publish_result.rc}")
        if hasattr(publish_result, "is_published") and not publish_result.is_published():
            raise RuntimeError("MQTT publish did not complete before timeout")

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline and len(messages) < 10:
            time.sleep(0.05)
        result = {
            "success": True,
            "topic": command_topic,
            "command_topic": command_topic,
            "qos": qos,
            "retain": retain,
            "bytes": len(payload.encode("utf-8")),
            "state_messages": list(messages),
            "dropped_messages": dropped_messages,
            "dropped_bytes": dropped_bytes,
        }
        if dropped_messages:
            result["warning"] = "One or more MQTT messages were dropped by inbound payload safety limits."
        return result
    finally:
        _safe_close_client(client)


def _handle_mqtt_publish(args: dict, **kw) -> str:
    try:
        topic = _validate_topic(args.get("topic", ""), allow_wildcards=False)
        payload = _payload_to_text(args.get("payload", ""))
        qos = _bounded_int(args.get("qos"), default=0, minimum=0, maximum=2, name="qos")
        retain = _strict_bool(
            args["retain"] if "retain" in args else False,
            default=False,
            name="retain",
        )
        return json.dumps({"result": _publish(topic, payload, qos=qos, retain=retain)})
    except Exception as exc:
        return tool_error(str(exc))


def _handle_mqtt_subscribe_recent(args: dict, **kw) -> str:
    try:
        topic_filter = _validate_topic(args.get("topic_filter", ""), allow_wildcards=True)
        timeout_seconds = _bounded_float(args.get("timeout_seconds"), default=5.0, minimum=0.01, maximum=30.0, name="timeout_seconds")
        max_messages = _bounded_int(args.get("max_messages"), default=10, minimum=1, maximum=50, name="max_messages")
        qos = _bounded_int(args.get("qos"), default=0, minimum=0, maximum=2, name="qos")
        result = _subscribe_recent(topic_filter, timeout_seconds=timeout_seconds, max_messages=max_messages, qos=qos)
        return json.dumps({"result": result})
    except Exception as exc:
        return tool_error(str(exc))


def _handle_mqtt_device_command(args: dict, **kw) -> str:
    try:
        command_topic = _validate_topic(args.get("command_topic", ""), allow_wildcards=False)
        payload = _payload_to_text(args.get("payload", ""))
        qos = _bounded_int(args.get("qos"), default=0, minimum=0, maximum=2, name="qos")
        retain = _strict_bool(
            args["retain"] if "retain" in args else False,
            default=False,
            name="retain",
        )
        state_filter = (args.get("state_topic_filter") or "").strip()
        if state_filter:
            validated_filter = _validate_topic(state_filter, allow_wildcards=True)
            timeout_seconds = _bounded_float(args.get("timeout_seconds"), default=5.0, minimum=0.01, maximum=30.0, name="timeout_seconds")
            command_result = _command_and_wait(
                command_topic,
                payload,
                state_topic_filter=validated_filter,
                timeout_seconds=timeout_seconds,
                qos=qos,
                retain=retain,
            )
            return json.dumps({"result": command_result})
        publish_result = _publish(command_topic, payload, qos=qos, retain=retain)
        return json.dumps({"result": {**publish_result, "command_topic": command_topic, "state_messages": []}})
    except Exception as exc:
        return tool_error(str(exc))


MQTT_PUBLISH_SCHEMA = {
    "name": "mqtt_publish",
    "description": "Publish a payload to an MQTT topic for IoT sensors, actuators, or device commands.",
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "MQTT publish topic, e.g. devices/lamp/cmd. Wildcards are not allowed."},
            "payload": {"description": "String, number, boolean, object, or array payload. Objects are encoded as compact JSON."},
            "qos": {"type": "integer", "description": "MQTT QoS 0, 1, or 2. Default 0."},
            "retain": {"type": "boolean", "description": "Set MQTT retain flag. Default false."},
        },
        "required": ["topic", "payload"],
    },
}

MQTT_SUBSCRIBE_RECENT_SCHEMA = {
    "name": "mqtt_subscribe_recent",
    "description": "Listen briefly to an MQTT topic/filter and return retained or newly published sensor messages.",
    "parameters": {
        "type": "object",
        "properties": {
            "topic_filter": {"type": "string", "description": "MQTT topic filter, e.g. sensors/+/temperature or devices/#."},
            "timeout_seconds": {"type": "number", "description": "How long to listen, 0.01-30 seconds. Default 5."},
            "max_messages": {"type": "integer", "description": "Maximum messages to return, 1-50. Default 10."},
            "qos": {"type": "integer", "description": "MQTT subscription QoS 0, 1, or 2. Default 0."},
        },
        "required": ["topic_filter"],
    },
}

MQTT_DEVICE_COMMAND_SCHEMA = {
    "name": "mqtt_device_command",
    "description": "Publish an MQTT device command and optionally wait briefly for state/ack messages.",
    "parameters": {
        "type": "object",
        "properties": {
            "command_topic": {"type": "string", "description": "MQTT command topic, e.g. devices/lamp/cmd. Wildcards are not allowed."},
            "payload": {"description": "Command payload. Objects are encoded as compact JSON."},
            "state_topic_filter": {"type": "string", "description": "Optional MQTT topic/filter subscribed before command publication to capture immediate state or ACK messages."},
            "timeout_seconds": {"type": "number", "description": "How long to wait for state messages, 0.01-30 seconds. Default 5."},
            "qos": {"type": "integer", "description": "MQTT publish QoS 0, 1, or 2. Default 0."},
            "retain": {"type": "boolean", "description": "Set retain flag on command publish. Default false."},
        },
        "required": ["command_topic", "payload"],
    },
}


registry.register(
    name="mqtt_publish",
    toolset="mqtt",
    schema=MQTT_PUBLISH_SCHEMA,
    handler=_handle_mqtt_publish,
    check_fn=_check_mqtt_available,
    requires_env=["MQTT_HOST"],
    emoji="📡",
)

registry.register(
    name="mqtt_subscribe_recent",
    toolset="mqtt",
    schema=MQTT_SUBSCRIBE_RECENT_SCHEMA,
    handler=_handle_mqtt_subscribe_recent,
    check_fn=_check_mqtt_available,
    requires_env=["MQTT_HOST"],
    emoji="📡",
)

registry.register(
    name="mqtt_device_command",
    toolset="mqtt",
    schema=MQTT_DEVICE_COMMAND_SCHEMA,
    handler=_handle_mqtt_device_command,
    check_fn=_check_mqtt_available,
    requires_env=["MQTT_HOST"],
    emoji="📡",
)
