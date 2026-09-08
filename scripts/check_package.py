#!/usr/bin/env python3
"""Check the public package boundary and headline synthetic results."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str) -> Path:
    target = ROOT / path
    if not target.exists():
        raise SystemExit(f"Missing required artifact: {path}")
    return target


def main() -> None:
    required = [
        "README.md",
        "CITATION.cff",
        "docs/review-2/Team1_Review2_OCEL.pptx",
        "docs/review-2/Team1_Initial_Draft_Report.docx",
        "synthetic/src/team1_synthetic_ocel.py",
        "synthetic/src/analyze_team1_synthetic.py",
        "synthetic/data/manifest.json",
        "synthetic/results/experiment_summary.json",
        "demo/app/page.tsx",
        "demo/package.json",
    ]
    for item in required:
        require(item)

    manifest = json.loads(require("synthetic/data/manifest.json").read_text())
    summary = json.loads(require("synthetic/results/experiment_summary.json").read_text())
    assert manifest["synthetic"] is True
    assert summary["configuration"]["synthetic"] is True
    assert summary["configuration"]["seed"] == 4971
    assert all(s["validation"]["dangling_e2o"] == 0 for s in manifest["scenarios"].values())
    assert all(s["validation"]["dangling_o2o"] == 0 for s in manifest["scenarios"].values())
    assert summary["anomaly_detection"]["macro_f1"] == 0.977
    assert summary["observability"]["cross_object_observability_coverage"]["ablation"][-1]["cooc_pct"] == 100.0

    hosting = json.loads(require("demo/.openai/hosting.json").read_text())
    if "project_id" in hosting:
        raise SystemExit("Deployment-specific Sites project_id must not be published")
    if (ROOT / "demo/.env").exists():
        raise SystemExit("Secret-bearing demo environment file is present")
    print("Repository package check passed: synthetic boundary and required artifacts verified.")


if __name__ == "__main__":
    main()
