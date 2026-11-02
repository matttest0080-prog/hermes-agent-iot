"""Security floors refresh affected pins without unlocking unrelated packages."""
import pytest

from scripts.regen_pi2_locks import old_constraints, refreshed_dependency_pins


@pytest.mark.parametrize("old,expected", [("1.0", {"transport": "2.0"}), ("2.1", {})])
def test_reviewed_floor_refreshes_only_violations(tmp_path, old, expected):
    lock = tmp_path / "old.lock"
    lock.write_text(f"transport=={old}\nunrelated==1.0\n")
    (tmp_path / "uv.lock").write_text('''
[[package]]
name = "transport"
version = "2.0"
[[package]]
name = "unrelated"
version = "9.0"
''')
    preferred = refreshed_dependency_pins(
        tmp_path, lock, ["core==1.0"], ["transport>=2.0,<3"],
    )
    assert preferred == expected
    constraints = old_constraints(lock, {"core"}, preferred)
    assert "unrelated==1.0" in constraints
    assert f"transport=={expected.get('transport', old)}" in constraints
