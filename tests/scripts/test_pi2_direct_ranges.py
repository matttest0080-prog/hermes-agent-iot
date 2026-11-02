"""Profile ranges keep compatible pins, including interpreter-specific splits."""
from scripts.regen_pi2_locks import (
    explicit_version_targets, old_constraints, refreshed_dependency_pins,
)


def test_compatible_direct_range_is_not_floated_by_an_artifact_closure(tmp_path):
    lock = tmp_path / "old.lock"
    lock.write_text('transport==1.0 ; python_version < "3.12" \\\n'
                    '    --hash=sha256:' + 'a' * 64 + '\n'
                    'transport==1.5 ; python_version >= "3.12" \\\n'
                    '    --hash=sha256:' + 'b' * 64 + '\n'
                    'unrelated==1.0\n')
    (tmp_path / "uv.lock").write_text('''
[[package]]
name = "browser"
version = "2.0"
dependencies = [{name = "transport"}]
[[package]]
name = "transport"
version = "2.0"
[[package]]
name = "unrelated"
version = "9.0"
''')
    requirements = ["browser @ https://example.invalid/browser.whl", "transport>=1,<3"]
    preferred = refreshed_dependency_pins(tmp_path, lock, requirements)
    assert preferred == {"browser": "2.0"}
    assert old_constraints(lock, explicit_version_targets(requirements), preferred) == [
        'transport==1.0 ; python_version < "3.12"',
        'transport==1.5 ; python_version >= "3.12"',
        'unrelated==1.0',
    ]


def test_changed_range_floor_refreshes_from_reviewed_lock(tmp_path):
    lock = tmp_path / "old.lock"
    lock.write_text("transport==1.0\n")
    (tmp_path / "uv.lock").write_text('''
[[package]]
name = "transport"
version = "2.0"
''')
    requirements = ["transport>=2,<3"]
    preferred = refreshed_dependency_pins(tmp_path, lock, requirements)
    assert preferred == {"transport": "2.0"}
    assert old_constraints(lock, explicit_version_targets(requirements), preferred) == ["transport==2.0"]
