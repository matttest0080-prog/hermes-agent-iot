"""The published wheel must contain no direct-URL Requires-Dist lines.

PyPI rejects every direct reference, including ones gated behind an extra.
The source tree keeps them for Android (psutil) and the KittenTTS backend;
the release wheel rewrites/drops only those known lines and updates RECORD.
"""

import base64
import csv
import hashlib
import io
import zipfile

from scripts.sanitize_release_wheel import sanitize_wheel

PSUTIL_GIT = (
    "psutil @ git+https://github.com/giampaolo/psutil.git@"
    "380bd2b59c67b0e1b04bbf3a90b11744f4f96644 ; sys_platform == \"android\""
)
KITTENTTS_URL = (
    "kittentts @ https://github.com/KittenML/KittenTTS/releases/download/0.8.1/"
    "kittentts-0.8.1-py3-none-any.whl ; extra == \"kittentts\""
)
MISAKI_GIT = (
    "misaki[en] @ git+https://github.com/NousResearch/misaki.git@"
    "f03fd2be7346952a83d3d4845c217fc7667f322d ; extra == \"kittentts\""
)


def _record_hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _build_wheel(path) -> dict[str, bytes]:
    files = {
        "demo/__init__.py": b"",
        "demo-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\n",
        "demo-1.0.dist-info/METADATA": (
            "Metadata-Version: 2.1\n"
            "Name: demo\n"
            "Version: 1.0\n"
            f"Requires-Dist: {PSUTIL_GIT}\n"
            f"Requires-Dist: {KITTENTTS_URL}\n"
            f"Requires-Dist: {MISAKI_GIT}\n"
            "Requires-Dist: soundfile==0.14.0; extra == \"kittentts\"\n"
        ).encode(),
    }
    rows = [[name, _record_hash(data), str(len(data))] for name, data in files.items()]
    rows.append(["demo-1.0.dist-info/RECORD", "", ""])
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    files["demo-1.0.dist-info/RECORD"] = out.getvalue().encode()
    with zipfile.ZipFile(path, "w") as wheel:
        for name, data in files.items():
            wheel.writestr(name, data)
    return files


def test_sanitizer_removes_every_direct_url_and_updates_record(tmp_path):
    wheel = tmp_path / "demo-1.0-py3-none-any.whl"
    _build_wheel(wheel)

    assert sanitize_wheel(wheel) is True
    with zipfile.ZipFile(wheel) as archive:
        assert archive.testzip() is None
        metadata = archive.read("demo-1.0.dist-info/METADATA").decode()
        record = archive.read("demo-1.0.dist-info/RECORD").decode()

    assert " @ " not in metadata
    assert 'psutil==7.2.2; sys_platform == "android"' in metadata
    assert "kittentts @ " not in metadata
    assert "misaki[en] @ " not in metadata
    assert 'soundfile==0.14.0; extra == "kittentts"' in metadata

    updated = metadata.encode()
    row = next(row for row in csv.reader(io.StringIO(record)) if row[0].endswith("METADATA"))
    assert row[1] == _record_hash(updated)
    assert row[2] == str(len(updated))


def test_sanitizer_is_idempotent(tmp_path):
    wheel = tmp_path / "demo-1.0-py3-none-any.whl"
    _build_wheel(wheel)
    assert sanitize_wheel(wheel) is True
    assert sanitize_wheel(wheel) is False
