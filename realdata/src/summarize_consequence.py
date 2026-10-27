#!/usr/bin/env python3
"""Aggregate results/consequence/*.json into per-log and per-notion tables (CSV + Markdown).

Run: python3 -I realdata/src/summarize_consequence.py
"""

from __future__ import annotations

import csv
import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results" / "consequence"


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 3) if xs else None


def lo(xs):
    xs = [x for x in xs if x is not None]
    return round(min(xs), 3) if xs else None


def main() -> None:
    log_rows, notion_rows = [], []
    for f in sorted(SRC.glob("*.json")):
        r = json.loads(f.read_text())
        ns = r["notions"]
        c4 = [(n["case_type"], x) for n in ns for x in n["C4_entity_rankings"]]
        for n in ns:
            notion_rows.append({
                "log": r["log"], "case_type": n["case_type"], "covered_events": n["covered_events"],
                "act_visible_share": n["C1_activities_visible_share"], "act_rank_rho_all": n["C1_activity_rank_rho"], "act_rank_rho_dup_only": n["C1_dup_only_rho"],
                "df_pair_duplication": n["C2_pair_duplication"], "df_edge_rho_dup_only": n["C2_dup_only_edge_rho"], "df_max_inflation_top10": n["C2_max_inflation_top10_edges"],
                "df_spurious_edge_mass": n.get("C2_spurious_edge_mass_vs_children"), "variants_per_case": n["C3_variants"]["variants_per_case"],
                "top10_variant_coverage": n["C3_variants"]["top10_variant_coverage"],
                "entity_rho_visible_median": med([x["rho_visible_only"] for x in n["C4_entity_rankings"]]),
                "entity_invisible_share_median": med([x["objects_invisible_share"] for x in n["C4_entity_rankings"]]),
            })
        log_rows.append({
            "log": r["log"], "notions": len(ns),
            "activity_visible_share_median": med([n["C1_activities_visible_share"] for n in ns]),
            "activity_rank_rho_all_median": med([n["C1_activity_rank_rho"] for n in ns]), "activity_rank_rho_all_min": lo([n["C1_activity_rank_rho"] for n in ns]),
            "activity_rank_rho_dup_only_min": lo([n["C1_dup_only_rho"] for n in ns]),
            "df_pair_duplication_max": max(n["C2_pair_duplication"] for n in ns), "df_edge_rho_dup_only_min": lo([n["C2_dup_only_edge_rho"] for n in ns]),
            "df_spurious_edge_mass_max": max([n.get("C2_spurious_edge_mass_vs_children") or 0 for n in ns]),
            "entity_pairs": len(c4), "entity_rho_visible_median": med([x["rho_visible_only"] for _, x in c4]), "entity_rho_visible_min": lo([x["rho_visible_only"] for _, x in c4]),
            "entity_invisible_share_median": med([x["objects_invisible_share"] for _, x in c4]),
        })
    for name, rows in (("consequence_by_log", log_rows), ("consequence_by_notion", notion_rows)):
        with (ROOT / "results" / f"{name}.csv").open("w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    hdr = list(log_rows[0])
    md = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)] + ["| " + " | ".join(str(r[k]) for k in hdr) + " |" for r in log_rows]
    (ROOT / "results" / "consequence_by_log.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
