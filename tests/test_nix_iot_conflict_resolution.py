from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_NIX = ROOT / "nix" / "python.nix"
PACKAGES_NIX = ROOT / "nix" / "packages.nix"


def test_uv2nix_selects_exactly_one_modal_vercel_conflict_branch() -> None:
    """Each uv2nix package must select one side of the lock conflict."""
    text = PYTHON_NIX.read_text(encoding="utf-8")

    assert 'conflictResolution = if lib.elem "modal" dependency-groups then "modal" else "vercel";' in text
    assert "hermes-agent-iot = dependency-groups ++ [ conflictResolution ];" in text


def test_default_nix_package_uses_vercel_and_exposes_modal_separately() -> None:
    """The default full closure cannot request both conflicting extras."""
    text = PACKAGES_NIX.read_text(encoding="utf-8")
    full_groups = text.split("full = minimal.override {", 1)[1].split("# matrix is Linux-only", 1)[0]

    assert '"vercel"' in full_groups
    assert '"modal"' not in full_groups
    assert 'modal = minimal.override {' in text
    assert 'extraDependencyGroups = [ "modal" ];' in text
