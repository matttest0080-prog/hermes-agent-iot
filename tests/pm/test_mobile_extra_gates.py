"""Wheel-only extras refuse unsupported targets before changing environments."""
from packaging.markers import default_environment
import pytest

from pm import extras


@pytest.mark.parametrize("system,platform_system,machine", [
    ("android", "Android", "aarch64"),
    ("linux", "Linux", "armv7l"),
])
def test_native_engines_refuse_mobile_but_portable_audio_stays_available(
    monkeypatch, system, platform_system, machine
):
    monkeypatch.setattr(extras, "_PLATFORM_GATES", None)
    facts = {**default_environment(), "sys_platform": system,
             "platform_system": platform_system, "platform_machine": machine}
    for name in ("google-meet", "stt-whisper", "wake-openwakeword", "piper", "kittentts"):
        assert not extras.extra_supported(name, environment=facts, importable=lambda _: False), name
    for name in ("voice", "audio-io"):
        assert extras.extra_supported(name, environment=facts, importable=lambda _: False), name
