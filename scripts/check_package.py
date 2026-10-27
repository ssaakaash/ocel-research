#!/usr/bin/env python3
"""Check the public package boundary: required artifacts, dataset manifest, and no tracked raw data."""

from __future__ import annotations

import json
import subprocess
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
        "docs/research/Journal_Paper_Research_Plan.md",
        "docs/research/Journal_Manuscript_Draft.md",
        "realdata/README.md",
        "realdata/sources.json",
        "realdata/requirements.txt",
        "realdata/src/cooc.py",
        "realdata/src/registry.py",
        "realdata/src/run_cooc.py",
    ]
    for item in required:
        require(item)

    sources = json.loads(require("realdata/sources.json").read_text(encoding="utf-8"))["sources"]
    for src in sources:
        for field in ("id", "doi", "license", "title"):
            if not src.get(field):
                raise SystemExit(f"realdata/sources.json: source {src.get('id')!r} lacks {field!r}")
        if "CC-BY" not in src["license"]:
            raise SystemExit(f"realdata/sources.json: {src['id']} is not marked CC-BY; review its licence before use")

    # Downloaded or derived third-party data must never be tracked.
    if (ROOT / ".git").exists():
        tracked = subprocess.run(["git", "ls-files", "realdata/raw", "realdata/ocel", "realdata/.venv"],
                                 cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        if tracked:
            raise SystemExit(f"Raw/derived third-party data is tracked in git: {tracked[:5]}")
    for env_file in ROOT.rglob(".env"):
        if ".venv" not in env_file.parts and "raw" not in env_file.parts:
            raise SystemExit(f"Secret-bearing environment file is present: {env_file.relative_to(ROOT)}")
    print(f"Repository package check passed: {len(required)} artifacts, {len(sources)} licensed sources, no tracked raw data.")


if __name__ == "__main__":
    main()
