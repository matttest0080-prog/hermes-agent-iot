#!/usr/bin/env python3
"""Make a release wheel acceptable to PyPI without losing the source pin.

PyPI rejects any ``Requires-Dist`` that contains a direct URL, including ones
gated behind an extra.  The source tree needs those pins for Android 3.13+
(psutil, upstream #2891) and the KittenTTS backend (kittentts + misaki), and
they must stay for source/Termux installs.  The published wheel cannot carry
them: replace the core psutil line with the latest registry release, drop the
two optional-backend lines, and update RECORD so the wheel still validates.

Fail closed on any other direct dependency: silently stripping one would hide a
second PyPI rejection until after the release is built.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

PSUTIL_REPLACEMENT = 'psutil==7.2.2; sys_platform == "android"'
# Optional backends whose upstream wheels are not on PyPI. Their source pins
# stay in pyproject.toml; PyPI cannot carry them in any extra, so the published
# wheel drops these two lines and keeps the rest of the kittentts extra.
DROP_PREFIXES = (
    "kittentts @ https://github.com/KittenML/KittenTTS/releases/download/",
    "misaki[en] @ git+https://github.com/NousResearch/misaki.git@",
)
_PSUTIL_LINE = re.compile(
    r"^Requires-Dist: psutil @ git\+https://github\.com/giampaolo/psutil\.git@"
    r"[0-9a-f]+ ; (?P<marker>.+)$"
)


def _record_hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _rewrite_metadata(lines: list[str]) -> tuple[list[str], bool]:
    rewritten: list[str] = []
    changed = False
    for line in lines:
        if not (line.startswith("Requires-Dist:") and " @ " in line):
            rewritten.append(line)
            continue
        if _PSUTIL_LINE.match(line):
            suffix = "\n" if line.endswith("\n") else ""
            rewritten.append(f"Requires-Dist: {PSUTIL_REPLACEMENT}{suffix}")
            changed = True
            continue
        if any(line.startswith(f"Requires-Dist: {prefix}") for prefix in DROP_PREFIXES):
            print(f"dropping PyPI-incompatible optional dependency: {line.strip()}")
            changed = True
            continue
        raise SystemExit(
            "refusing to sanitize: unexpected direct dependency in wheel metadata: "
            + line.strip()
        )
    remaining = [
        line for line in rewritten
        if line.startswith("Requires-Dist:") and " @ " in line
    ]
    if remaining:
        raise SystemExit(
            "refusing to sanitize: direct dependency still present:\n"
            + "\n".join(remaining)
        )
    if not changed:
        print("no direct dependencies; unchanged")
    return rewritten, changed


def sanitize_wheel(path: Path) -> bool:
    """Rewrite *path* in place. Returns True when metadata changed."""
    with zipfile.ZipFile(path) as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]

    metadata_names = [
        info.filename for info, _ in entries
        if info.filename.endswith(".dist-info/METADATA")
    ]
    if len(metadata_names) != 1:
        raise SystemExit(f"{path}: expected exactly one .dist-info/METADATA")
    metadata_name = metadata_names[0]
    metadata_index = next(
        index for index, (info, _) in enumerate(entries)
        if info.filename == metadata_name
    )
    metadata = entries[metadata_index][1].decode("utf-8")
    lines = metadata.splitlines(keepends=True)
    rewritten, changed = _rewrite_metadata(lines)
    if not changed:
        print(f"{path}: no direct dependencies; unchanged")
        return False
    new_metadata = "".join(rewritten).encode("utf-8")
    if any(
        line.startswith("Requires-Dist:") and " @ " in line
        for line in rewritten
    ):
        raise SystemExit(f"{path}: direct dependency still present after rewrite")
    entries[metadata_index] = (entries[metadata_index][0], new_metadata)

    record_name = metadata_name.removesuffix("METADATA") + "RECORD"
    record_index = next(
        (index for index, (info, _) in enumerate(entries) if info.filename == record_name),
        None,
    )
    if record_index is None:
        raise SystemExit(f"{path}: missing {record_name}")
    record_text = entries[record_index][1].decode("utf-8")
    rows = list(csv.reader(io.StringIO(record_text)))
    found = False
    for row in rows:
        if row and row[0] == metadata_name:
            row[1] = _record_hash(new_metadata)
            row[2] = str(len(new_metadata))
            found = True
            break
    if not found:
        raise SystemExit(f"{path}: {metadata_name} is absent from RECORD")
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    entries[record_index] = (entries[record_index][0], out.getvalue().encode("utf-8"))

    temporary = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(temporary, "w") as target:
        for info, data in entries:
            target.writestr(info, data)
    temporary.replace(path)
    print(f"{path}: replaced Android psutil direct URL with {PSUTIL_REPLACEMENT}")
    return True


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: sanitize_release_wheel.py WHEEL [WHEEL ...]", file=sys.stderr)
        return 2
    for raw in argv:
        path = Path(raw)
        if not path.is_file() or path.suffix != ".whl":
            raise SystemExit(f"not a wheel: {path}")
        sanitize_wheel(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
