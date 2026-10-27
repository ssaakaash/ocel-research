#!/usr/bin/env python3
"""Per-log summary of flattening distortion (one row per log) from results/distortion/*.json.

  case notions        object types whose flat log covers at least 1,000 events
  duplication         share of events duplicated by flattening = copies per event above 1.05
  type pairs          ordered pairs (T, U) with at least 10 U-objects; "shared" means at least half of the U-objects
                      take part in events of two or more T-objects

Run: python3 -I realdata/src/summarize_log_level.py
"""

from __future__ import annotations

import csv
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "distortion"
MIN_NOTION_EVENTS, DUP_THRESHOLD, MIN_U_OBJECTS, SHARED = 1000, 1.05, 10, 0.5


def main() -> None:
    rows = []
    for f in sorted(SRC.glob("*.json")):
        rep = json.loads(f.read_text())
        events = rep["events"]
        notions = [c for c in rep["case_notions"] if events * (1 - c["deficiency"]) >= MIN_NOTION_EVENTS]
        pairs = [c for c in rep["coupling"] if c["u_objects"] >= MIN_U_OBJECTS]
        copies = [c["copies_per_event"] for c in notions]
        rows.append({
            "log": rep["log"], "events": events, "objects": rep["objects"], "types": len(rep["object_types"]),
            "objects_per_event": round(rep["objects_per_event_mean"], 3),
            "case_notions_covering_ge1000_events": len(notions),
            "notions_with_event_duplication_gt5pct": sum(1 for x in copies if x > DUP_THRESHOLD),
            "max_copies_per_event": round(max(copies), 3), "median_copies_per_event": round(st.median(copies), 3),
            "median_deficiency": round(st.median(c["deficiency"] for c in notions), 3),
            "type_pairs": len(pairs), "pairs_with_ge50pct_shared_objects": sum(1 for c in pairs if c["share_u_in_multiple_cases"] >= SHARED),
        })
    out = ROOT / "results" / "log_level_summary.csv"
    with out.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out.relative_to(ROOT)} ({len(rows)} logs)")


if __name__ == "__main__":
    main()
