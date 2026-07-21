"""Regression test for #33175: switch_model() must roll back to the pre-swap
state if the client rebuild raises.

Before the fix, ``agent.model`` and ``agent.provider`` were assigned BEFORE
the client rebuild was attempted, with no try/except to restore them on
failure.  An exception during ``build_anthropic_client`` / OpenAI client
construction left the agent with the new model+provider name but the OLD
client — producing HTTP 400s like "claude-sonnet-4-6 is not supported on
openai-codex" on the next turn.

These tests exercise both branches (openai_chat_completions and
anthropic_messages) and assert that every mutated field returns to its
pre-swap value when the rebuild raises.
"""

from unittest.mock import MagicMock, patch

import pytest

from run_agent import AIAgent


def _make_agent_openrouter():
    """Agent on openrouter (openai-compatible) with sentinel client + kwargs."""
    agent = AIAgent.__new__(AIAgent)

    agent.provider = "openrouter"
    agent.model = "x-ai/grok-4"
    agent.base_url = "https://openrouter.ai/api/v1"
    agent.api_key = "or-key-original"
    agent.api_mode = "chat_completions"
    agent.client = MagicMock(name="OriginalOpenRouterClient")
    agent._client_kwargs = {
        "api_key": "or-key-original",
        "base_url": "https://openrouter.ai/api/v1",
    }
    agent.context_compressor = None
    agent._anthropic_api_key = ""
    agent._anthropic_base_url = None
    agent._anthropic_client = None
    agent._is_anthropic_oauth = False
    agent._cached_system_prompt = "cached"
    agent._primary_runtime = {}
    agent._fallback_activated = False
    agent._fallback_index = 0
    agent._fallback_chain = []
    agent._fallback_model = None
    agent._config_context_length = None

    return agent


def _make_agent_anthropic():
    """Agent on native anthropic with a sentinel anthropic client."""
    agent = AIAgent.__new__(AIAgent)

    agent.provider = "anthropic"
    agent.model = "claude-sonnet-4-5"
    agent.base_url = "https://api.anthropic.com"
    agent.api_key = "sk-ant-original"
    agent.api_mode = "anthropic_messages"
    agent.client = None
    agent._client_kwargs = {}
    agent.context_compressor = None
    agent._anthropic_api_key = "sk-ant-original"
    agent._anthropic_base_url = "https://api.anthropic.com"
    agent._anthropic_client = MagicMock(name="OriginalAnthropicClient")
    agent._is_anthropic_oauth = False
    agent._cached_system_prompt = "cached"
    agent._primary_runtime = {}
    agent._fallback_activated = False
    agent._fallback_index = 0
    agent._fallback_chain = []
    agent._fallback_model = None
    agent._config_context_length = None

    return agent


def test_openai_client_rebuild_failure_rolls_back_to_original_state():
    """When OpenAI client construction fails, every mutated field must restore."""
    agent = _make_agent_openrouter()

    original_client = agent.client
    original_kwargs = dict(agent._client_kwargs)

    # _create_openai_client raises mid-swap (simulates bad key / network error)
    def boom(*_a, **_kw):
        raise RuntimeError("simulated client build failure")

    agent._create_openai_client = boom

    with patch("hermes_cli.timeouts.get_provider_request_timeout", return_value=None):
        with pytest.raises(RuntimeError, match="simulated client build failure"):
            agent.switch_model(
                new_model="openai/gpt-5",
                new_provider="openai-codex",
                api_key="codex-key-new",
                base_url="https://chatgpt.com/backend-api/codex/responses",
                api_mode="chat_completions",
            )

    # Core invariant: agent state is unchanged from before the call
    assert agent.model == "x-ai/grok-4"
    assert agent.provider == "openrouter"
    assert agent.base_url == "https://openrouter.ai/api/v1"
    assert agent.api_mode == "chat_completions"
    assert agent.api_key == "or-key-original"
    assert agent.client is original_client
    assert agent._client_kwargs == original_kwargs


def test_anthropic_client_rebuild_failure_rolls_back_to_original_state():
    """When build_anthropic_client raises, every mutated field must restore."""
    agent = _make_agent_anthropic()

    original_anthropic_client = agent._anthropic_client
    original_anthropic_key = agent._anthropic_api_key
    original_anthropic_base = agent._anthropic_base_url

    with (
        patch(
            "agent.anthropic_adapter.build_anthropic_client",
            side_effect=RuntimeError("simulated anthropic build failure"),
        ),
        patch(
            "agent.anthropic_adapter.resolve_anthropic_token",
            return_value="sk-ant-resolved",
        ),
        patch("agent.anthropic_adapter._is_oauth_token", return_value=False),
        patch("hermes_cli.timeouts.get_provider_request_timeout", return_value=None),
    ):
        with pytest.raises(RuntimeError, match="simulated anthropic build failure"):
            agent.switch_model(
                new_model="claude-opus-4-6",
                new_provider="opencode-zen",
                api_key="zen-key-new",
                base_url="https://opencode.example/v1",
                api_mode="anthropic_messages",
            )

    # Anthropic-specific state restored
    assert agent._anthropic_client is original_anthropic_client
    assert agent._anthropic_api_key == original_anthropic_key
    assert agent._anthropic_base_url == original_anthropic_base

    # Core state also restored
    assert agent.model == "claude-sonnet-4-5"
    assert agent.provider == "anthropic"
    assert agent.base_url == "https://api.anthropic.com"
    assert agent.api_mode == "anthropic_messages"
    assert agent.api_key == "sk-ant-original"


def test_cross_branch_anthropic_to_openai_rebuild_failure_rolls_back():
    """Switching from anthropic_messages to chat_completions: failure must
    restore the anthropic state, not leave the agent half-converted."""
    agent = _make_agent_anthropic()

    original_anthropic_client = agent._anthropic_client

    def boom(*_a, **_kw):
        raise RuntimeError("openai client failed")

    agent._create_openai_client = boom

    with patch("hermes_cli.timeouts.get_provider_request_timeout", return_value=None):
        with pytest.raises(RuntimeError, match="openai client failed"):
            agent.switch_model(
                new_model="x-ai/grok-4",
                new_provider="openrouter",
                api_key="or-key-new",
                base_url="https://openrouter.ai/api/v1",
                api_mode="chat_completions",
            )

    # Anthropic client preserved (not nulled by the openai branch)
    assert agent._anthropic_client is original_anthropic_client
    assert agent.model == "claude-sonnet-4-5"
    assert agent.provider == "anthropic"
    assert agent.api_mode == "anthropic_messages"
    assert agent.base_url == "https://api.anthropic.com"


def test_successful_switch_still_works_after_rollback_refactor():
    """Sanity check: the try/except wrapper hasn't broken the happy path."""
    agent = _make_agent_openrouter()

    new_client = MagicMock(name="NewClient")
    agent._create_openai_client = lambda *_a, **_kw: new_client

    with patch("hermes_cli.timeouts.get_provider_request_timeout", return_value=None):
        agent.switch_model(
            new_model="openai/gpt-5",
            new_provider="openrouter",
            api_key="or-key-new",
            base_url="https://openrouter.ai/api/v1",
            api_mode="chat_completions",
        )

    assert agent.model == "openai/gpt-5"
    assert agent.provider == "openrouter"
    assert agent.api_key == "or-key-new"
    assert agent.client is new_client


class _MutatingCompressor:
    def __init__(self, *, raise_after_mutation: bool = False):
        self.model = "x-ai/grok-4"
        self.context_length = 128_000
        self.base_url = "https://openrouter.ai/api/v1"
        self.api_key = "or-key-original"
        self.provider = "openrouter"
        self.api_mode = "chat_completions"
        self.threshold_tokens = 64_000
        self.raise_after_mutation = raise_after_mutation

    def update_model(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)
        self.threshold_tokens = int(self.context_length * 0.5)
        if self.raise_after_mutation:
            raise RuntimeError("compressor mutated then failed")


def _make_floor_guard_agent(*, compressor):
    agent = _make_agent_openrouter()
    agent.context_compressor = compressor
    agent._minimum_tool_context_length = 2_048
    agent._credential_pool = MagicMock(name="OriginalPool", provider="openrouter")
    agent._use_prompt_caching = False
    agent._use_native_cache_layout = False
    agent._anthropic_prompt_cache_policy = lambda **_kwargs: (True, True)
    agent._ensure_lmstudio_runtime_loaded = lambda *_args, **_kwargs: None
    agent._create_openai_client = lambda *_args, **_kwargs: MagicMock(name="NewClient")
    return agent


def test_switch_rejects_context_below_profile_floor_and_rolls_back_runtime():
    compressor = _MutatingCompressor()
    agent = _make_floor_guard_agent(compressor=compressor)
    original_pool = agent._credential_pool
    original_client = agent.client

    with (
        patch("agent.model_metadata.get_model_context_length", return_value=1_024),
        patch("hermes_cli.timeouts.get_provider_request_timeout", return_value=None),
    ):
        with pytest.raises(ValueError, match="configured minimum 2,048"):
            agent.switch_model(
                new_model="tiny-model",
                new_provider="openrouter",
                api_key="new-key",
                base_url="https://openrouter.ai/api/v1",
                api_mode="chat_completions",
            )

    assert agent.model == "x-ai/grok-4"
    assert agent.provider == "openrouter"
    assert agent.api_key == "or-key-original"
    assert agent.client is original_client
    assert agent._credential_pool is original_pool
    assert agent._use_prompt_caching is False
    assert agent._use_native_cache_layout is False
    assert compressor.model == "x-ai/grok-4"
    assert compressor.context_length == 128_000
    assert compressor.threshold_tokens == 64_000


def test_switch_rolls_back_compressor_mutation_and_prompt_cache_flags():
    compressor = _MutatingCompressor(raise_after_mutation=True)
    agent = _make_floor_guard_agent(compressor=compressor)
    original_pool = agent._credential_pool

    with (
        patch("agent.model_metadata.get_model_context_length", return_value=8_192),
        patch("hermes_cli.timeouts.get_provider_request_timeout", return_value=None),
    ):
        with pytest.raises(RuntimeError, match="compressor mutated then failed"):
            agent.switch_model(
                new_model="valid-small-model",
                new_provider="openrouter",
                api_key="new-key",
                base_url="https://openrouter.ai/api/v1",
                api_mode="chat_completions",
            )

    assert agent.model == "x-ai/grok-4"
    assert agent.provider == "openrouter"
    assert agent._credential_pool is original_pool
    assert agent._use_prompt_caching is False
    assert agent._use_native_cache_layout is False
    assert compressor.model == "x-ai/grok-4"
    assert compressor.context_length == 128_000
    assert compressor.base_url == "https://openrouter.ai/api/v1"
    assert compressor.api_key == "or-key-original"
    assert compressor.threshold_tokens == 64_000
