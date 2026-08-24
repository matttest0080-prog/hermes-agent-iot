#!/usr/bin/env python3
"""Validate and summarize an OSV Scanner SARIF document."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUPPORTED_SARIF_VERSIONS = {"2.1.0"}


def summarize_sarif(document: Any) -> tuple[int, list[str]]:
    """Return finding count/details, rejecting incomplete SARIF structures."""
    if not isinstance(document, dict):
        raise ValueError("SARIF root must be an object")
    version = document.get("version")
    if version not in SUPPORTED_SARIF_VERSIONS:
        raise ValueError(f"unsupported or missing SARIF version: {version!r}")
    runs = document.get("runs")
    if not isinstance(runs, list):
        raise ValueError("SARIF runs must be a list")

    details: list[str] = []
    count = 0
    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            raise ValueError(f"SARIF run {index} must be an object")
        results = run.get("results")
        if not isinstance(results, list):
            raise ValueError(f"SARIF run {index} results must be a list")
        for result_index, result in enumerate(results):
            if not isinstance(result, dict):
                raise ValueError(
                    f"SARIF run {index} result {result_index} must be an object"
                )
            count += 1
            rule_id = result.get("ruleId", "unknown")
            message_value = result.get("message", {})
            message = (
                message_value.get("text", "")
                if isinstance(message_value, dict)
                else ""
            )
            locations = result.get("locations", [])
            location = locations[0] if isinstance(locations, list) and locations else {}
            physical = (
                location.get("physicalLocation", {})
                if isinstance(location, dict)
                else {}
            )
            artifact = (
                physical.get("artifactLocation", {})
                if isinstance(physical, dict)
                else {}
            )
            uri = artifact.get("uri", "") if isinstance(artifact, dict) else ""
            details.append(f"- {rule_id} in {uri}: {message}")
    return count, details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sarif", type=Path)
    parser.add_argument("--details-json", action="store_true")
    args = parser.parse_args()

    with args.sarif.open(encoding="utf-8") as handle:
        document = json.load(handle)
    count, details = summarize_sarif(document)
    if args.details_json:
        print(json.dumps("\n".join(details[:20])))
    else:
        print(count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
