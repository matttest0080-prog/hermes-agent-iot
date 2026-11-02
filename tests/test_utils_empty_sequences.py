"""Emptying a commented config list must preserve valid YAML and the original on failure."""
import pytest

import hermes_yaml as yaml
from hermes_cli.config import atomic_config_replace


@pytest.mark.parametrize("nested", [False, True])
def test_empty_commented_sequence_roundtrips_without_corrupting_its_next_sibling(tmp_path, nested):
    path = tmp_path / "config.yaml"
    body = "fallbacks:\n  # Keep this operator guidance\n  - model: backup\nnext: {enabled: true}\n"
    source = "routing:\n" + "".join("  " + line for line in body.splitlines(True)) if nested else body
    path.write_text(source, encoding="utf-8")
    data = yaml.safe_load(source)
    owner = data["routing"] if nested else data
    owner["fallbacks"] = []
    for _ in range(2):
        atomic_config_replace(path, data)
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == data
        assert "# Keep this operator guidance" in path.read_text(encoding="utf-8")


def test_invalid_serializer_output_never_replaces_existing_config(tmp_path, monkeypatch):
    import utils
    path = tmp_path / "config.yaml"
    original = "# operator settings\nvalue: 1\n"
    path.write_text(original, encoding="utf-8")
    real_load = utils._roundtrip_load

    class BrokenDumper:
        def dump(self, _config, output):
            output.write("value: [unterminated\n")

    def load(target):
        _, config = real_load(target)
        return BrokenDumper(), config

    monkeypatch.setattr(utils, "_roundtrip_load", load)
    with pytest.raises(ValueError, match="YAML"):
        atomic_config_replace(path, {"value": 2})
    assert path.read_text(encoding="utf-8") == original
