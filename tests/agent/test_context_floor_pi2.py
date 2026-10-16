"""Fork-only context-floor (Pi2 profile) tests.

These used to be the IoT fork's additions inside the upstream test modules. They live here so
``minimum_tool_context_length`` stays covered without growing upstream files past their
code-health FILE_LINES caps. The ``agent`` fixture and ``_make_tool_defs`` are imported from
the upstream run_agent module, so both files build the same agent.
"""

from types import SimpleNamespace

import pytest
from unittest.mock import MagicMock, patch

from agent.context_compressor import ContextCompressor
from run_agent import AIAgent
from tests.agent.test_run_agent import _make_tool_defs, _mock_response


@pytest.fixture
def agent():
    """Minimal AIAgent with mocked OpenAI client and tool loading.

    Same construction as the upstream ``tests/agent/test_run_agent.py`` fixture; kept local
    so this module needs no cross-module fixture plumbing.
    """
    with (
        patch("model_tools.get_tool_definitions", return_value=_make_tool_defs("web_search")),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        built = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        built.client = MagicMock()
        return built


def _setup_agent(instance):
    """Common setup for run_conversation tests (verbatim from the upstream class)."""
    instance._cached_system_prompt = "You are helpful."
    instance._use_prompt_caching = False
    instance.compression_enabled = False
    instance.save_trajectories = False

# moved from tests/agent/test_run_agent.py
def test_pi2_context_floor_applies_during_real_agent_initialization():
    config = {
        "model": {"context_length": 4096},
        "agent": {"minimum_tool_context_length": 2048},
    }
    with (
        patch("model_tools.get_tool_definitions", return_value=_make_tool_defs("terminal")),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
        patch("hermes_cli.config.load_config_readonly", return_value=config),
    ):
        initialized = AIAgent(
            api_key="test-key-1234567890",
            provider="custom",
            model="tiny-local-model",
            base_url="http://localhost:11434/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )

    assert initialized.context_compressor.context_length == 4096
    assert initialized._minimum_tool_context_length == 2048

# moved from tests/agent/test_run_agent.py
def test_pi2_context_floor_rejects_context_below_profile_minimum():
    config = {
        "model": {"context_length": 1024},
        "agent": {"minimum_tool_context_length": 2048},
    }
    with (
        patch("model_tools.get_tool_definitions", return_value=_make_tool_defs("terminal")),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
        patch("hermes_cli.config.load_config_readonly", return_value=config),
        pytest.raises(ValueError, match="configured minimum 2,048"),
    ):
        AIAgent(
            api_key="test-key-1234567890",
            provider="custom",
            model="tiny-local-model",
            base_url="http://localhost:11434/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )

# moved from tests/agent/test_run_agent.py
def test_invalid_boolean_context_floor_fails_closed_to_default():
    config = {
        "model": {"context_length": 4096},
        "agent": {"minimum_tool_context_length": True},
    }
    with (
        patch("model_tools.get_tool_definitions", return_value=_make_tool_defs("terminal")),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
        patch("hermes_cli.config.load_config_readonly", return_value=config),
        pytest.raises(ValueError, match="configured minimum 64,000"),
    ):
        AIAgent(
            api_key="test-key-1234567890",
            provider="custom",
            model="tiny-local-model",
            base_url="http://localhost:11434/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )

# moved from tests/agent/test_run_agent.py
def test_configured_small_ollama_context_floor_allows_pi2_profile(agent):
    _setup_agent(agent)
    agent.model = "tiny-local-model"
    agent.provider = "custom"
    agent.base_url = "http://localhost:11434/v1"
    agent._ollama_num_ctx = 4096
    agent._minimum_tool_context_length = 2048
    resp = _mock_response(content="small context ok", finish_reason="stop")
    agent.client.chat.completions.create.return_value = resp

    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("hello")

    assert result["completed"] is True
    assert result["failed"] is False
    assert result["final_response"] == "small context ok"
    assert agent.client.chat.completions.create.called

# moved from tests/agent/test_run_agent.py
def test_configured_ollama_context_floor_uses_profile_value(agent):
    _setup_agent(agent)
    agent.model = "tiny-local-model"
    agent.provider = "custom"
    agent.base_url = "http://localhost:11434/v1"
    agent._ollama_num_ctx = 4096
    agent._minimum_tool_context_length = 8192

    with (
        patch.object(agent, "_persist_session"),
        patch.object(agent, "_save_trajectory"),
        patch.object(agent, "_cleanup_task_resources"),
    ):
        result = agent.run_conversation("hello")

    assert result["failed"] is True
    assert result["api_calls"] == 0
    assert "needs at least 8,192 tokens" in result["final_response"]
    assert "profile lowers Hermes' tool-context floor to 8,192" in result["final_response"]

# moved from tests/agent/test_model_metadata.py
def test_local_context_cache_uses_configured_profile_floor():
    from agent.model_metadata import _maybe_cache_local_context_length

    with (
        patch(
            "agent.model_metadata.get_minimum_tool_context_length",
            return_value=2048,
        ),
        patch("agent.model_metadata.save_context_length") as mock_save,
    ):
        _maybe_cache_local_context_length(
            "tiny-local",
            "http://pi2.local:11434/v1",
            4096,
        )

    mock_save.assert_called_once_with(
        "tiny-local",
        "http://pi2.local:11434/v1",
        4096,
    )

# moved from tests/agent/test_model_metadata.py
@pytest.mark.parametrize("value", [None, True, False, 0, -1, "0", "-8", "bad", object()])
def test_minimum_tool_context_length_invalid_values_fail_closed(value):
    from agent.model_metadata import MINIMUM_CONTEXT_LENGTH, get_minimum_tool_context_length

    agent = SimpleNamespace(_minimum_tool_context_length=value)
    assert get_minimum_tool_context_length(agent) == MINIMUM_CONTEXT_LENGTH

# moved from tests/agent/test_model_metadata.py
def test_minimum_tool_context_length_accepts_positive_integer_string():
    from agent.model_metadata import get_minimum_tool_context_length

    assert get_minimum_tool_context_length(
        SimpleNamespace(_minimum_tool_context_length="2048")
    ) == 2048

# moved from tests/agent/test_context_compressor.py
def test_threshold_uses_configured_profile_floor():
    compressor = ContextCompressor(
        model="tiny-local",
        quiet_mode=True,
        config_context_length=4096,
        minimum_context_length=2048,
    )

    assert compressor.minimum_context_length == 2048
    assert compressor.threshold_tokens == 3072

# moved from tests/agent/test_auxiliary_client.py
def test_compression_task_uses_configured_profile_floor():
    from agent.auxiliary_client import _task_minimum_context_length

    with patch(
        "hermes_cli.config.load_config_readonly",
        return_value={"agent": {"minimum_tool_context_length": 2048}},
    ):
        assert _task_minimum_context_length("compression") == 2048
