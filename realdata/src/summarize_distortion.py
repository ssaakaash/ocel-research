#!/usr/bin/env python3
"""Combine results/distortion/*.json into one table (CSV + Markdown) for the paper.

Run: python3 -I realdata/src/summarize_distortion.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "distortion"


def main() -> None:
    rows = []
    for f in sorted(SRC.glob("*.json")):
        rep = json.loads(f.read_text())
        coup = rep.get("coupling", [])
        for c in rep["case_notions"]:
            shared = [x for x in coup if x["case_type"] == c["case_type"]]
            rows.append({
                "log": rep["log"], "events": rep["events"], "objects_per_event": rep["objects_per_event_mean"], "case_type": c["case_type"], "cases": c["cases"],
                "deficiency": c["deficiency"], "convergence_share": c["convergence_share"], "copies_per_event": c["copies_per_event"],
                "max_activity_inflation": c["max_activity_inflation"], "divergence_share": c["divergence_share"],
                "variants_per_case": c.get("variants_per_case"), "nested_children": "/".join(c.get("nested_children") or []),
                "cross_instance_adjacency": c.get("cross_instance_adjacency"),
                "max_other_in_multiple_cases": max((x["share_u_in_multiple_cases"] for x in shared), default=None),
            })
    out = ROOT / "results" / "distortion_summary.csv"
    with out.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    md = ["| log | case notion | cases | deficiency | convergence | copies/event | divergence | variants/case | nested children | cross-instance adjacency |", "|---|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    for r in rows:
        md.append(f"| {r['log']} | {r['case_type']} | {r['cases']:,} | {r['deficiency']:.3f} | {r['convergence_share']:.3f} | {r['copies_per_event']:.2f} | {r['divergence_share']:.3f} | {r['variants_per_case']} | {r['nested_children'] or '-'} | {r['cross_instance_adjacency'] if r['cross_instance_adjacency'] is not None else '-'} |")
    (ROOT / "results" / "distortion_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
