"""Pi2 lock generation keeps profile scope and refreshes reviewed dependency closures."""
from __future__ import annotations

import pytest

from scripts.regen_pi2_locks import (
    add_piwheels_hashes,
    expand_profile,
    linux_armv7_requirements,
    old_constraints,
    piwheels_arm_hashes,
    refreshed_dependency_pins,
)


def test_profile_expansion_preserves_requirements_and_rejects_excluded_backends():
    metadata = {
        "project": {
            "dependencies": ["core==1.0", "uvloop==1.0"],
            "optional-dependencies": {
                "minimal": ["transport==2.0"],
                "iot": ["hermes-agent-iot[minimal]==0.22.5.post1", "pillow-heif==1.4.0"],
            },
        },
    }
    assert expand_profile(metadata, "iot") == ["core==1.0", "transport==2.0"]
    with pytest.raises(KeyError):
        expand_profile(metadata, "not-a-profile")


def test_linux_selection_removes_inactive_source_pins_but_preserves_python_splits():
    requirements = [
        "transport==1.0",
        "psutil @ git+https://example.invalid/psutil.git@1234567890abcdef ; sys_platform == 'android'",
        "windows-only==1.0; sys_platform == 'win32'",
        "cpython-only==1.0; platform_python_implementation == 'CPython'",
        "newer==1.0; python_version >= '3.12'",
        "older==1.0; python_version < '3.12'",
        "patch-specific==1.0; python_full_version >= '3.13.5'",
    ]
    assert linux_armv7_requirements(requirements) == [
        requirements[i] for i in (0, 3, 4, 5, 6)
    ]


def test_profile_expansion_stops_self_reference_cycles():
    metadata = {"project": {"optional-dependencies": {
        "minimal": ["hermes-agent-iot[minimal]", "core==1.0"],
    }}}
    assert expand_profile(metadata, "minimal") == ["core==1.0"]


def test_security_pin_refresh_changes_only_the_affected_dependency_closure(tmp_path):
    lock = tmp_path / "old.lock"
    lock.write_text("mcp==2.2.0\nmcp-types==2.2.0\nunrelated==1.0\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text('''
[[package]]
name = "mcp"
version = "2.3.0"
dependencies = [{name = "mcp-types"}]
[[package]]
name = "mcp-types"
version = "2.3.0"
[[package]]
name = "unrelated"
version = "2.0"
''', encoding="utf-8")
    preferred = refreshed_dependency_pins(tmp_path, lock, ["mcp==2.3.0"])
    assert preferred == {"mcp": "2.3.0", "mcp-types": "2.3.0"}
    assert old_constraints(lock, {"mcp"}, preferred) == ["mcp-types==2.3.0", "unrelated==1.0"]
    assert refreshed_dependency_pins(tmp_path, lock, ["mcp==2.2.0"]) == {}


def test_direct_artifact_refresh_uses_reviewed_closure_without_unlocking_unrelated_pins(tmp_path):
    lock = tmp_path / "old.lock"
    lock.write_text("browser-harness==0.1.13\ntransport==1.0\nunrelated==1.0\n")
    (tmp_path / "uv.lock").write_text('''
[[package]]
name = "browser-harness"
version = "0.1.13.post1"
dependencies = [{name = "transport"}]
[[package]]
name = "transport"
version = "2.0"
[[package]]
name = "unrelated"
version = "3.0"
''')
    preferred = refreshed_dependency_pins(
        tmp_path, lock, ["browser-harness @ https://example.invalid/browser.whl#sha256=" + "a" * 64]
    )
    assert preferred == {"browser-harness": "0.1.13.post1", "transport": "2.0"}
    assert old_constraints(lock, {"browser-harness"}, preferred) == ["transport==2.0", "unrelated==1.0"]


def test_piwheels_hashes_are_version_scoped_and_missing_packages_are_not_accepted_as_other_versions():
    cache = {"cffi": [
        ("cffi-2.0.0-cp313-cp313-linux_armv7l.whl", "a" * 64),
        ("cffi-1.17.1-cp313-cp313-linux_armv7l.whl", "b" * 64),
    ]}
    assert piwheels_arm_hashes("cffi", "2.0.0", cache) == {"a" * 64}
    assert piwheels_arm_hashes("cffi", "9.9.9", cache) == set()


def test_hash_merge_is_idempotent_and_keeps_the_original_digest(tmp_path):
    lock = tmp_path / "profile.lock"
    lock.write_text("cffi==2.0.0 \\\n    --hash=sha256:" + "a" * 64 + "\n", encoding="utf-8")
    cache = {"cffi": [("cffi-2.0.0-cp313-cp313-linux_armv7l.whl", "b" * 64)]}
    add_piwheels_hashes(lock, cache)
    first = lock.read_text(encoding="utf-8")
    add_piwheels_hashes(lock, cache)
    assert lock.read_text(encoding="utf-8") == first
    assert first.count("--hash=sha256:") == 2
    assert "a" * 64 in first and "b" * 64 in first
