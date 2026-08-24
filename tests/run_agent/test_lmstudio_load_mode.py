from types import SimpleNamespace
from typing import Any, cast

import pytest

from run_agent import AIAgent


def _agent(load_mode="explicit"):
    return SimpleNamespace(
        provider="lmstudio",
        model="test/model",
        base_url="http://127.0.0.1:1234/v1",
        api_key="",
        lmstudio_load_mode=load_mode,
        _config_context_length=None,
        context_compressor=None,
        api_mode="chat_completions",
    )


def test_lmstudio_jit_load_mode_skips_explicit_preload(monkeypatch):
    calls = []

    def fake_ensure(*args, **kwargs):
        calls.append((args, kwargs))
        return 64000

    monkeypatch.setattr("hermes_cli.models.ensure_lmstudio_model_loaded", fake_ensure)

    AIAgent._ensure_lmstudio_runtime_loaded(cast(Any, _agent("jit")))

    assert calls == []


def test_lmstudio_explicit_load_mode_preserves_preload(monkeypatch):
    calls = []

    def fake_ensure(*args, **kwargs):
        calls.append((args, kwargs))
        return 64000

    monkeypatch.setattr("hermes_cli.models.ensure_lmstudio_model_loaded", fake_ensure)

    AIAgent._ensure_lmstudio_runtime_loaded(cast(Any, _agent("explicit")))

    assert len(calls) == 1
    assert calls[0][0][:3] == ("test/model", "http://127.0.0.1:1234/v1", "")
    assert calls[0][0][3] == 64000


def test_missing_lmstudio_load_mode_defaults_to_explicit(monkeypatch):
    calls = []
    agent = _agent()
    delattr(agent, "lmstudio_load_mode")

    def fake_ensure(*args, **kwargs):
        calls.append((args, kwargs))
        return 64000

    monkeypatch.setattr("hermes_cli.models.ensure_lmstudio_model_loaded", fake_ensure)

    AIAgent._ensure_lmstudio_runtime_loaded(cast(Any, agent))

    assert len(calls) == 1


@pytest.mark.parametrize("profile_floor", [2_048, 8_192])
def test_lmstudio_explicit_preload_uses_instance_profile_floor(monkeypatch, profile_floor):
    calls = []
    agent = _agent("explicit")
    agent._minimum_tool_context_length = profile_floor

    def fake_ensure(*args, **kwargs):
        calls.append((args, kwargs))
        return profile_floor

    monkeypatch.setattr("hermes_cli.models.ensure_lmstudio_model_loaded", fake_ensure)

    AIAgent._ensure_lmstudio_runtime_loaded(cast(Any, agent))

    assert calls[0][0][3] == profile_floor


def test_lmstudio_explicit_preload_uses_maximum_of_pin_and_profile_floor(monkeypatch):
    calls = []
    agent = _agent("explicit")
    agent._minimum_tool_context_length = 8_192
    agent._config_context_length = 2_048

    def fake_ensure(*args, **kwargs):
        calls.append((args, kwargs))
        return 8_192

    monkeypatch.setattr("hermes_cli.models.ensure_lmstudio_model_loaded", fake_ensure)

    result = AIAgent._ensure_lmstudio_runtime_loaded(cast(Any, agent), 2_048)

    assert calls[0][0][3] == 8_192
    assert result == 8_192


def test_lmstudio_verified_runtime_context_is_authoritative_over_lower_pin():
    assert AIAgent._effective_lmstudio_context_length(2_048, 8_192) == 8_192
