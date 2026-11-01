"""The daemon's hermes CLI remains reachable without shadowing a bound client's tools."""
import os

import pytest

from agent.session_client_env import client_env_scope
from tools.environments import local


@pytest.mark.parametrize("client_env,local_attach", [(None, True), ({}, True), ({"PATH": "client"}, True), ({}, False)])
def test_hermes_cli_directory_is_a_fallback_for_bound_sessions(tmp_path, monkeypatch, client_env, local_attach):
    client = str(tmp_path / "client")
    runtime = str(tmp_path / "runtime")
    monkeypatch.setattr(local, "_resolve_hermes_bin_dir", lambda: runtime)
    monkeypatch.setattr(local, "_HERMES_BIN_DIR_IS_PAYLOAD", False)
    with client_env_scope(client_env, local=local_attach):
        actual = local._prepend_hermes_bin_dir(client).split(os.pathsep)
    assert actual == ([runtime, client] if client_env is None else [client, runtime])
    assert local._prepend_hermes_bin_dir(client).split(os.pathsep) == [runtime, client]


def test_payload_launcher_precedence_is_not_weakened(tmp_path, monkeypatch):
    client, payload = str(tmp_path / "client"), str(tmp_path / "payload")
    monkeypatch.setattr(local, "_resolve_hermes_bin_dir", lambda: payload)
    monkeypatch.setattr(local, "_HERMES_BIN_DIR_IS_PAYLOAD", True)
    with client_env_scope({"PATH": client}):
        assert local._prepend_hermes_bin_dir(client).split(os.pathsep) == [payload, client]
