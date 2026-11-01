"""Profile-aware minimum context validation for constrained runtimes."""

from agent.model_metadata import is_local_endpoint


def _enforce_minimum_context(agent):
    # Reject windows below the configured tool-workflow floor (default 64K); an explicit
    # positive model.context_length on LM Studio is allowed below the floor.
    _ctx = getattr(agent.context_compressor, "context_length", 0)
    # A local Ollama server serves num_ctx, not the GGUF's advertised window: a Modelfile or
    # model.ollama_num_ctx at 64K+ is a usable window even when the metadata says 40K (#100437).
    # Only a local endpoint can honour num_ctx, so a stale override never admits a hosted model.
    if agent._ollama_num_ctx and agent.base_url and is_local_endpoint(agent.base_url):
        _ctx = max(_ctx or 0, agent._ollama_num_ctx)
    _allow_lmstudio_explicit_below_floor = (
        str(agent.provider or "").strip().lower() == "lmstudio"
        and isinstance(agent._config_context_length, int)
        and not isinstance(agent._config_context_length, bool)
        and agent._config_context_length > 0
    )
    if _allow_lmstudio_explicit_below_floor:
        return
    from agent.model_metadata import get_minimum_tool_context_length

    # The floor is configurable (agent.minimum_tool_context_length; the Pi2 profiles lower it),
    # so it is never taken from a module constant. The wording stays split by endpoint the way
    # upstream has it: a local server's window is its own runtime setting, so it gets the
    # server-side remedy (#87075), while a hosted route gets model advice.
    minimum_context_length = get_minimum_tool_context_length(agent)
    if not _ctx or _ctx >= minimum_context_length:
        return
    floor_k = minimum_context_length // 1000
    if agent.base_url and is_local_endpoint(agent.base_url):
        lead = (
            f"which is below the configured minimum {minimum_context_length:,} "
            f"required by Hermes Agent."
        )
        remedy = (
            f"Your local server is serving a {_ctx:,}-token window.  Start it with at least "
            f"{floor_k}K context (llama.cpp: -c {minimum_context_length}; vLLM: --max-model-len; "
            f"Ollama: OLLAMA_CONTEXT_LENGTH={minimum_context_length} or a Modelfile num_ctx), "
            f"or set model.ollama_num_ctx in config.yaml to the window it really serves "
            f"(at least {floor_k}K)."
        )
    else:
        lead = f"which is below the minimum {minimum_context_length:,} required by Hermes Agent."
        remedy = (
            f"Choose a model with at least {floor_k}K context.  If your server "
            f"reports a window smaller than the model's true window, set "
            f"model.context_length in config.yaml to the real value "
            f"(this must be at least {floor_k}K)."
        )
    raise ValueError(
        f"Model {agent.model} has a context window of {_ctx:,} tokens, {lead}  {remedy}"
    )
