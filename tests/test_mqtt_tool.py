from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class FakeMessage:
    def __init__(self, topic: str, payload: bytes, qos: int = 0, retain: bool = False) -> None:
        self.topic = topic
        self.payload = payload
        self.qos = qos
        self.retain = retain


class DecodeBomb(bytes):
    def decode(self, *args, **kwargs):
        raise AssertionError("oversized payload must not be decoded")


class FakePublishResult:
    rc = 0

    def __init__(self, client) -> None:
        self.client = client

    def wait_for_publish(self, timeout: float | None = None) -> bool:
        if not self.client.loop_running:
            raise RuntimeError("network loop must run while waiting for publish")
        self.timeout = timeout
        return True

    def is_published(self) -> bool:
        return True


class FakeClient:
    queued_messages: list[FakeMessage] = []
    published: list[tuple[str, str, int, bool]] = []
    subscribed: list[tuple[str, int]] = []
    connected: list[tuple[str, int, int]] = []
    username_pw: list[tuple[str, str | None]] = []
    tls_enabled = False
    disconnected = 0
    events: list[str] = []
    subscribe_reason_codes: list[int] = [0]
    deliver_on_loop_start = True

    def __init__(self, client_id: str = "", protocol=None) -> None:
        self.client_id = client_id
        self.on_message = None
        self.on_connect = None
        self.on_subscribe = None
        self.loop_running = False
        self.active_subscription = False

    @classmethod
    def reset(cls) -> None:
        cls.queued_messages = []
        cls.published = []
        cls.subscribed = []
        cls.connected = []
        cls.username_pw = []
        cls.tls_enabled = False
        cls.disconnected = 0
        cls.events = []
        cls.subscribe_reason_codes = [0]
        cls.deliver_on_loop_start = True

    def username_pw_set(self, username: str, password: str | None = None) -> None:
        type(self).username_pw.append((username, password))

    def tls_set(self) -> None:
        type(self).tls_enabled = True

    def connect(self, host: str, port: int, keepalive: int = 60) -> None:
        type(self).connected.append((host, port, keepalive))

    def disconnect(self) -> None:
        type(self).disconnected += 1

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> FakePublishResult:
        type(self).events.append("publish")
        type(self).published.append((topic, payload, qos, retain))
        if self.active_subscription and self.on_message:
            for msg in list(type(self).queued_messages):
                self.on_message(self, None, msg)
        return FakePublishResult(self)

    def subscribe(self, topic_filter: str, qos: int = 0):
        type(self).events.append("subscribe")
        self.active_subscription = True
        type(self).subscribed.append((topic_filter, qos))
        if self.on_subscribe:
            self.on_subscribe(self, None, 1, list(type(self).subscribe_reason_codes))
        return (0, 1)

    def loop_start(self) -> None:
        self.loop_running = True
        type(self).events.append("loop_start")
        if self.on_connect:
            self.on_connect(self, None, {}, 0)
        if type(self).deliver_on_loop_start:
            for msg in list(type(self).queued_messages):
                if self.on_message:
                    self.on_message(self, None, msg)

    def loop_stop(self) -> None:
        type(self).events.append("loop_stop")
        self.loop_running = False


class MQTTToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._mqtt_env_keys = [
            "MQTT_HOST",
            "MQTT_PORT",
            "MQTT_USERNAME",
            "MQTT_PASSWORD",
            "MQTT_CLIENT_ID",
            "MQTT_TLS",
            "MQTT_ALLOW_INSECURE_CREDENTIALS",
        ]
        self._mqtt_env_before = {key: os.environ.get(key) for key in self._mqtt_env_keys}
        from tools import mqtt_tool
        self._mqtt_client_factory_before = mqtt_tool._mqtt_client_factory
        for key in self._mqtt_env_keys:
            os.environ.pop(key, None)
        FakeClient.reset()

    def tearDown(self) -> None:
        from tools import mqtt_tool
        mqtt_tool._mqtt_client_factory = self._mqtt_client_factory_before
        for key in self._mqtt_env_keys:
            previous = self._mqtt_env_before[key]
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous

    def test_availability_requires_mqtt_host(self) -> None:
        from tools import mqtt_tool

        self.assertFalse(mqtt_tool._check_mqtt_available())
        os.environ["MQTT_HOST"] = "broker.local"
        self.assertTrue(mqtt_tool._check_mqtt_available())

    def test_publish_uses_env_config_and_validates_topic(self) -> None:
        from tools import mqtt_tool

        mqtt_tool._mqtt_client_factory = lambda: FakeClient
        os.environ.update({
            "MQTT_HOST": "broker.local",
            "MQTT_PORT": "1884",
            "MQTT_USERNAME": "iot-user",
            "MQTT_PASSWORD": "secret",
            "MQTT_TLS": "true",
        })

        result = json.loads(mqtt_tool._handle_mqtt_publish({
            "topic": "devices/lamp/cmd",
            "payload": "ON",
            "qos": 1,
            "retain": True,
        }))

        self.assertTrue(result["result"]["success"])
        self.assertEqual(FakeClient.connected, [("broker.local", 1884, 60)])
        self.assertEqual(FakeClient.username_pw, [("iot-user", "secret")])
        self.assertTrue(FakeClient.tls_enabled)
        self.assertEqual(FakeClient.published, [("devices/lamp/cmd", "ON", 1, True)])
        self.assertLess(FakeClient.events.index("loop_start"), FakeClient.events.index("publish"))
        self.assertLess(FakeClient.events.index("publish"), FakeClient.events.index("loop_stop"))

        invalid = json.loads(mqtt_tool._handle_mqtt_publish({"topic": "devices/+/cmd", "payload": "ON"}))
        self.assertIn("error", invalid)
        self.assertIn("wildcards", invalid["error"])

    def test_credentials_without_tls_fail_before_client_creation(self) -> None:
        from tools import mqtt_tool

        os.environ["MQTT_HOST"] = "broker.local"
        factory_calls = []
        mqtt_tool._mqtt_client_factory = lambda: factory_calls.append(True) or FakeClient

        for credential_key in ("MQTT_USERNAME", "MQTT_PASSWORD"):
            with self.subTest(credential_key=credential_key):
                os.environ[credential_key] = "secret"
                result = json.loads(mqtt_tool._handle_mqtt_publish({
                    "topic": "devices/lamp/cmd",
                    "payload": "ON",
                }))
                self.assertIn("error", result)
                self.assertIn("MQTT_TLS", result["error"])
                self.assertEqual(factory_calls, [])
                self.assertEqual(FakeClient.connected, [])
                os.environ.pop(credential_key)

    def test_insecure_credentials_require_explicit_opt_in(self) -> None:
        from tools import mqtt_tool

        mqtt_tool._mqtt_client_factory = lambda: FakeClient
        os.environ.update({
            "MQTT_HOST": "broker.local",
            "MQTT_USERNAME": "iot-user",
            "MQTT_PASSWORD": "secret",
            "MQTT_ALLOW_INSECURE_CREDENTIALS": "true",
        })

        result = json.loads(mqtt_tool._handle_mqtt_publish({
            "topic": "devices/lamp/cmd",
            "payload": "ON",
        }))

        self.assertTrue(result["result"]["success"])
        self.assertEqual(FakeClient.connected, [("broker.local", 1883, 60)])

    def test_subscribe_recent_collects_messages_without_requiring_broker_history(self) -> None:
        from tools import mqtt_tool

        mqtt_tool._mqtt_client_factory = lambda: FakeClient
        os.environ["MQTT_HOST"] = "broker.local"
        FakeClient.queued_messages = [
            FakeMessage("sensors/kitchen/temp", b"23.5", qos=1, retain=True),
            FakeMessage("sensors/kitchen/humidity", b"51", qos=0, retain=False),
        ]

        result = json.loads(mqtt_tool._handle_mqtt_subscribe_recent({
            "topic_filter": "sensors/kitchen/#",
            "timeout_seconds": 0.01,
            "max_messages": 5,
        }))

        self.assertEqual(result["result"]["count"], 2)
        self.assertEqual(FakeClient.subscribed, [("sensors/kitchen/#", 0)])
        self.assertEqual(result["result"]["messages"][0]["payload"], "23.5")
        self.assertTrue(result["result"]["messages"][0]["retain"])

    def test_subscribe_recent_drops_single_and_cumulative_payload_overflow_before_decode(self) -> None:
        from tools import mqtt_tool

        mqtt_tool._mqtt_client_factory = lambda: FakeClient
        os.environ["MQTT_HOST"] = "broker.local"
        FakeClient.queued_messages = [
            FakeMessage("sensors/oversized", DecodeBomb(b"12345")),
            FakeMessage("sensors/accepted", b"1234"),
            FakeMessage("sensors/aggregate-overflow", b"abc"),
        ]
        old_single = mqtt_tool._MAX_INBOUND_PAYLOAD_BYTES
        old_total = mqtt_tool._MAX_INBOUND_RESPONSE_BYTES
        mqtt_tool._MAX_INBOUND_PAYLOAD_BYTES = 4
        mqtt_tool._MAX_INBOUND_RESPONSE_BYTES = 6
        try:
            result = json.loads(mqtt_tool._handle_mqtt_subscribe_recent({
                "topic_filter": "sensors/#",
                "timeout_seconds": 0.01,
                "max_messages": 10,
            }))
        finally:
            mqtt_tool._MAX_INBOUND_PAYLOAD_BYTES = old_single
            mqtt_tool._MAX_INBOUND_RESPONSE_BYTES = old_total

        self.assertEqual([message["payload"] for message in result["result"]["messages"]], ["1234"])
        self.assertEqual(result["result"]["dropped_messages"], 2)
        self.assertEqual(result["result"]["dropped_bytes"], 8)
        self.assertIn("safety limit", result["result"]["warning"])

    def test_device_command_publishes_and_optionally_waits_for_state(self) -> None:
        from tools import mqtt_tool

        mqtt_tool._mqtt_client_factory = lambda: FakeClient
        os.environ["MQTT_HOST"] = "broker.local"
        FakeClient.queued_messages = [FakeMessage("devices/lamp/state", b"ON")]

        result = json.loads(mqtt_tool._handle_mqtt_device_command({
            "command_topic": "devices/lamp/cmd",
            "payload": "ON",
            "state_topic_filter": "devices/lamp/state",
            "timeout_seconds": 0.01,
        }))

        self.assertTrue(result["result"]["success"])
        self.assertEqual(FakeClient.published, [("devices/lamp/cmd", "ON", 0, False)])
        self.assertEqual(result["result"]["state_messages"][0]["payload"], "ON")
        self.assertLess(FakeClient.events.index("subscribe"), FakeClient.events.index("publish"))

    def test_device_command_drops_ack_payload_overflow_before_decode(self) -> None:
        from tools import mqtt_tool

        mqtt_tool._mqtt_client_factory = lambda: FakeClient
        os.environ["MQTT_HOST"] = "broker.local"
        FakeClient.deliver_on_loop_start = False
        FakeClient.queued_messages = [
            FakeMessage("devices/lamp/oversized", DecodeBomb(b"12345")),
            FakeMessage("devices/lamp/state", b"1234"),
            FakeMessage("devices/lamp/aggregate-overflow", b"abc"),
        ]
        old_single = mqtt_tool._MAX_INBOUND_PAYLOAD_BYTES
        old_total = mqtt_tool._MAX_INBOUND_RESPONSE_BYTES
        mqtt_tool._MAX_INBOUND_PAYLOAD_BYTES = 4
        mqtt_tool._MAX_INBOUND_RESPONSE_BYTES = 6
        try:
            result = json.loads(mqtt_tool._handle_mqtt_device_command({
                "command_topic": "devices/lamp/cmd",
                "payload": "ON",
                "state_topic_filter": "devices/lamp/#",
                "timeout_seconds": 0.01,
            }))
        finally:
            mqtt_tool._MAX_INBOUND_PAYLOAD_BYTES = old_single
            mqtt_tool._MAX_INBOUND_RESPONSE_BYTES = old_total

        self.assertEqual([message["payload"] for message in result["result"]["state_messages"]], ["1234"])
        self.assertEqual(result["result"]["dropped_messages"], 2)
        self.assertEqual(result["result"]["dropped_bytes"], 8)
        self.assertIn("safety limit", result["result"]["warning"])

    def test_device_command_does_not_publish_when_subscription_is_rejected(self) -> None:
        from tools import mqtt_tool

        mqtt_tool._mqtt_client_factory = lambda: FakeClient
        os.environ["MQTT_HOST"] = "broker.local"
        FakeClient.subscribe_reason_codes = [128]

        result = json.loads(mqtt_tool._handle_mqtt_device_command({
            "command_topic": "devices/lamp/cmd",
            "payload": "ON",
            "state_topic_filter": "devices/lamp/state",
            "timeout_seconds": 0.01,
        }))

        self.assertIn("error", result)
        self.assertIn("subscription rejected", result["error"])
        self.assertEqual(FakeClient.published, [])
        self.assertIn("loop_stop", FakeClient.events)
        self.assertEqual(FakeClient.disconnected, 1)

    def test_mqtt_toolset_is_resolvable(self) -> None:
        from toolsets import resolve_toolset

        self.assertCountEqual(
            resolve_toolset("mqtt"),
            ["mqtt_publish", "mqtt_subscribe_recent", "mqtt_device_command"],
        )

    def test_model_tool_discovery_requires_host_and_explicit_toolset(self) -> None:
        from model_tools import get_tool_definitions
        from tools.registry import invalidate_check_fn_cache

        invalidate_check_fn_cache()
        unavailable = get_tool_definitions(["mqtt"], [], quiet_mode=False)
        self.assertEqual(unavailable, [])

        os.environ["MQTT_HOST"] = "broker.example"
        invalidate_check_fn_cache()
        available = get_tool_definitions(
            ["mqtt"], [], quiet_mode=False, skip_tool_search_assembly=True
        )
        names = sorted(item["function"]["name"] for item in available)
        self.assertEqual(
            names,
            ["mqtt_device_command", "mqtt_publish", "mqtt_subscribe_recent"],
        )


if __name__ == "__main__":
    unittest.main()
