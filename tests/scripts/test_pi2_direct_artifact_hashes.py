"""pip must find the explicit lock hash for a wheel's exact Requires-Dist URL."""
from packaging.requirements import Requirement
import pytest

from scripts.regen_pi2_locks import preserve_direct_artifact_identity


@pytest.mark.parametrize("suffix", ["", " ; python_version >= '3.11'"])
@pytest.mark.parametrize("prefix", ["", "\ufeff"])
def test_export_restores_metadata_url_without_changing_hash_or_marker(tmp_path, suffix, prefix):
    url = "https://example.invalid/fixture.whl"
    digest = "a" * 64
    lock = tmp_path / "profile.lock"
    exported = f"fixture @ {url}{suffix} \\\n    --hash=sha256:{digest}\nunrelated==1.0\n"
    lock.write_text(prefix + exported)
    declared = f"fixture @ {url}#sha256={digest}{suffix}"
    preserve_direct_artifact_identity(lock, [declared])
    actual = lock.read_text()
    assert actual == exported.replace(url, url + "#sha256=" + digest)
    header = actual.split(" \\\n", 1)[0]
    assert Requirement(header).url == Requirement(declared).url
    preserve_direct_artifact_identity(lock, [declared])
    assert lock.read_text() == actual


@pytest.mark.parametrize("bad_url,bad_hash", [
    ("https://other.invalid/fixture.whl", "a" * 64),
    ("https://example.invalid/fixture.whl", "b" * 64),
])
def test_mismatched_artifact_or_digest_fails_without_rewriting(tmp_path, bad_url, bad_hash):
    lock = tmp_path / "profile.lock"
    exported = f"fixture @ {bad_url} \\\n    --hash=sha256:{bad_hash}\n"
    lock.write_text(exported)
    with pytest.raises(ValueError):
        preserve_direct_artifact_identity(lock, [
            "fixture @ https://example.invalid/fixture.whl#sha256=" + "a" * 64,
        ])
    assert lock.read_text() == exported
