from unittest.mock import patch


def test_local_llama_setup_uses_safe_llama_server_defaults():
    from hermes_cli import model_setup_flows

    config = {}
    with patch.object(model_setup_flows, "_model_flow_custom") as custom:
        model_setup_flows._model_flow_local_llama(config)

    custom.assert_called_once_with(
        config,
        preset={
            "base_url": "http://127.0.0.1:8080/v1",
            "api_key": "local",
            "model": "pi2-local",
        },
    )


def test_custom_flow_still_accepts_calls_without_preset():
    import inspect

    from hermes_cli import model_setup_flows

    parameter = inspect.signature(model_setup_flows._model_flow_custom).parameters["preset"]
    assert parameter.default is None
