from pathlib import Path

import pytest
import yaml

from scripts.osv_sarif_summary import summarize_sarif


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "osv-scanner.yml"


@pytest.fixture
def valid_sarif():
    return {"version": "2.1.0", "runs": [{"results": []}]}


def _steps():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["emit-status"]["steps"]


def test_emit_status_fails_closed_without_sarif_artifact():
    steps = _steps()
    download = next(step for step in steps if step["name"] == "Download SARIF result")
    emit = next(step for step in steps if step.get("id") == "emit")

    assert download.get("continue-on-error") is not True
    assert "SARIF result is missing" in emit["run"]
    assert "exit 1" in emit["run"]


def test_emit_status_uses_the_configured_sarif_filename():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    configured = workflow["jobs"]["scan"]["with"]["results-file-name"]
    emit = next(step for step in _steps() if step.get("id") == "emit")

    assert f"/tmp/osv-results/{configured}" in emit["run"]
    assert "/tmp/osv-results/results.sarif" not in emit["run"]


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"version": "2.1.0"},
        {"version": "2.1.0", "runs": {}},
        {"version": "2.1.0", "runs": [{}]},
        {"version": "2.1.0", "runs": [{"results": {}}]},
        {"version": "1.0.0", "runs": [{"results": []}]},
    ],
)
def test_sarif_summary_rejects_missing_or_invalid_structure(document):
    with pytest.raises(ValueError):
        summarize_sarif(document)


def test_sarif_summary_accepts_valid_zero_result_document(valid_sarif):
    assert summarize_sarif(valid_sarif) == (0, [])


def test_sarif_summary_counts_valid_results(valid_sarif):
    valid_sarif["runs"][0]["results"] = [
        {
            "ruleId": "GHSA-test",
            "message": {"text": "example"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "uv.lock"}
                    }
                }
            ],
        }
    ]

    assert summarize_sarif(valid_sarif) == (
        1,
        ["- GHSA-test in uv.lock: example"],
    )
