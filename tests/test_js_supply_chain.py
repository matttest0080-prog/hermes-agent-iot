"""Tests for scripts/check_js_supply_chain.py (exact pins + lifecycle scripts)."""
import json
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_js_supply_chain.py"


def run(repo, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def make_repo(tmp_path, *, dep_spec="1.2.3", lock_packages=None):
    write_json(tmp_path / "package.json", {"name": "fixture", "version": "1.0.0"})
    write_json(
        tmp_path / "pkg" / "package.json",
        {"name": "pkg", "version": "1.0.0", "dependencies": {"left-pad": dep_spec}},
    )
    write_json(
        tmp_path / "package-lock.json",
        {"lockfileVersion": 3, "packages": {"": {"name": "fixture"}, **(lock_packages or {})}},
    )
    return tmp_path


def test_exact_pin_check_rejects_a_range(tmp_path):
    repo = make_repo(tmp_path, dep_spec="^1.3.0")
    proc = run(repo)
    assert proc.returncode == 1, proc.stdout
    assert "left-pad=^1.3.0" in proc.stdout


def test_exact_pin_check_accepts_an_exact_version(tmp_path):
    repo = make_repo(tmp_path, dep_spec="1.3.0")
    proc = run(repo)
    assert proc.returncode == 0, proc.stdout
    assert "guard passed" in proc.stdout


def test_internal_workspace_references_are_allowed(tmp_path):
    repo = make_repo(tmp_path, dep_spec="workspace:*")
    proc = run(repo)
    assert proc.returncode == 0, proc.stdout


def test_lifecycle_script_gate_flags_a_new_install_script(tmp_path):
    repo = make_repo(
        tmp_path,
        lock_packages={"node_modules/evil": {"version": "9.9.9", "hasInstallScript": True}},
    )
    proc = run(repo, "--lifecycle")
    assert proc.returncode == 1, proc.stdout
    assert "evil@9.9.9" in proc.stdout


def test_update_records_the_baseline_and_then_passes(tmp_path):
    repo = make_repo(
        tmp_path,
        dep_spec="^1.3.0",
        lock_packages={"node_modules/evil": {"version": "9.9.9", "hasInstallScript": True}},
    )
    assert run(repo).returncode == 1
    assert run(repo, "--update").returncode == 0
    baseline = json.loads(
        (repo / "scripts" / "js-supply-chain-baseline.json").read_text(encoding="utf-8")
    )
    assert baseline["pinned_exceptions"] == ["pkg/package.json#dependencies#left-pad"]
    assert baseline["lifecycle"] == ["evil@9.9.9"]
    assert run(repo).returncode == 0
    # the gate is a ratchet: one more install script trips it again
    write_json(
        repo / "package-lock.json",
        {
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "fixture"},
                "node_modules/evil": {"version": "9.9.9", "hasInstallScript": True},
                "node_modules/evil2": {"version": "1.0.0", "hasInstallScript": True},
            },
        },
    )
    proc = run(repo, "--lifecycle")
    assert proc.returncode == 1, proc.stdout
    assert "evil2@1.0.0" in proc.stdout


def test_lifecycle_entries_are_matched_by_name_and_version_across_lockfiles(tmp_path):
    """Moving a dependency between lockfiles must not read as a new script."""
    repo = make_repo(tmp_path)
    write_json(
        repo / "web" / "package-lock.json",
        {"lockfileVersion": 3, "packages": {"node_modules/fsevents": {"version": "2.3.3", "hasInstallScript": True}}},
    )
    assert run(repo, "--lifecycle", "--update").returncode == 0
    write_json(
        repo / "package-lock.json",
        {"lockfileVersion": 3, "packages": {"node_modules/fsevents": {"version": "2.3.3", "hasInstallScript": True}}},
    )
    (repo / "web" / "package-lock.json").unlink()
    proc = run(repo, "--lifecycle")
    assert proc.returncode == 0, proc.stdout


def test_the_repository_itself_is_clean():
    """The checked-in tree must satisfy its own gate."""
    proc = run(REPO_ROOT)
    assert proc.returncode == 0, proc.stdout + proc.stderr
