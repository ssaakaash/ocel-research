#!/usr/bin/env python3
"""Print the three result tables of the manuscript (Markdown) from realdata/results.

Run: python3 -I scripts/review3/make_paper_tables.py
"""

from __future__ import annotations

import csv
from pathlib import Path

RES = Path(__file__).resolve().parents[2] / "realdata" / "results"
LABEL = {"crop": "CROP (Gerrit)", "oulad": "OULAD", "bundestag": "German Bundestag", "aoe2": "Age of Empires II", "ethereum": "Ethereum (window)", "angular_commits": "Angular commits", "enron": "Enron e-mail"}
DOMAIN = {"crop": "code review", "oulad": "education", "bundestag": "legislation", "aoe2": "game play", "ethereum": "blockchain", "angular_commits": "software commits", "enron": "e-mail"}
REGIME = {"crop": "star", "oulad": "star", "bundestag": "partitioned", "aoe2": "partitioned", "ethereum": "partitioned", "angular_commits": "fan-out", "enron": "fan-out"}
ORDER = ["crop", "oulad", "bundestag", "aoe2", "ethereum", "angular_commits", "enron"]


def rows(name: str) -> dict:
    with (RES / name).open(encoding="utf-8") as h:
        return {r["log"]: r for r in csv.DictReader(h)}


def f(x, nd=2) -> str:
    if x in (None, ""):
        return "-"
    v = round(float(x), nd)
    return f"{(v if v else 0.0):.{nd}f}"


def table(header: list[str], body: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    return "\n".join(out + ["| " + " | ".join(r) + " |" for r in body])


def main() -> None:
    L, C = rows("log_level_summary.csv"), rows("consequence_by_log.csv")
    t1 = table(["Log", "Domain", "Events", "Objects", "Object types", "Objects per event", "Analysed case notions"],
               [[LABEL[k], DOMAIN[k], f"{int(L[k]['events']):,}", f"{int(L[k]['objects']):,}", L[k]["types"], f(L[k]["objects_per_event"], 1), L[k]["case_notions_covering_ge1000_events"]] for k in ORDER])
    t2 = table(["Log", "Regime", "Median share of events dropped", "Median copies per event", "Largest copies per event", "Notions with over 5% duplication", "Type pairs sharing at least 50% of objects"],
               [[LABEL[k], REGIME[k], f"{100 * float(L[k]['median_deficiency']):.1f}%", f(L[k]["median_copies_per_event"]), f(L[k]["max_copies_per_event"]),
                 f"{L[k]['notions_with_event_duplication_gt5pct']} of {L[k]['case_notions_covering_ge1000_events']}", f"{L[k]['pairs_with_ge50pct_shared_objects']} of {L[k]['type_pairs']}"] for k in ORDER])
    t3 = table(["Log", "Notions", "Activities visible (median)", "Activity rank correlation vs whole process (median / lowest)", "Lowest, duplication only", "Largest edge duplication", "Lowest entity-rank correlation"],
               [[LABEL[k], C[k]["notions"], f(C[k]["activity_visible_share_median"]), f"{f(C[k]['activity_rank_rho_all_median'])} / {f(C[k]['activity_rank_rho_all_min'])}", f(C[k]["activity_rank_rho_dup_only_min"]),
                 f(C[k]["df_pair_duplication_max"]), f(C[k]["entity_rho_visible_min"])] for k in ORDER])
    print("TABLE 1\n" + t1 + "\n\nTABLE 2\n" + t2 + "\n\nTABLE 3\n" + t3 + "\n\nNARROWING\n" + narrowing())


def narrowing() -> str:
    """Narrowing counts of section 4.2: plausible case notions and threshold sensitivity."""
    with (RES / "consequence_by_notion.csv").open(encoding="utf-8") as h:
        cons = list(csv.DictReader(h))
    with (RES / "distortion_summary.csv").open(encoding="utf-8") as h:
        cover = {(r["log"], r["case_type"]): 1 - float(r["deficiency"]) for r in csv.DictReader(h)}
    for r in cons:
        r["cover"], r["vis"] = cover[(r["log"], r["case_type"])], float(r["act_visible_share"])
    out = []
    out.append("Widest case notion per log (most events covered): events covered, activities visible, rho vs whole process")
    for k in ORDER:
        w = max((r for r in cons if r["log"] == k), key=lambda r: (r["cover"], r["vis"]))
        out.append(f"  {LABEL[k]}: {w['case_type']}  {100 * w['cover']:.1f}%  {w['vis']:.2f}  {f(w['act_rank_rho_all'])}")
    for c in (0.3, 0.4, 0.5, 0.6, 0.7):
        p = [r for r in cons if r["cover"] >= c]
        narrow = [f"{LABEL[r['log']]} {r['case_type']} ({r['vis']:.2f})" for r in p if r["vis"] < 0.5]
        out.append(f"Notions covering >= {c:.0%} of events: {len(p)}; under half the activities visible: {len(narrow)} {narrow}")
    out.append("Activity-visibility threshold t: notions with visible share < t (of %d)" % len(cons))
    out.append("  " + ", ".join(f"t={t}: {sum(r['vis'] < t for r in cons)}" for t in (0.3, 0.4, 0.5, 0.6, 0.7)))
    out.append("Event cut-off m (raised from 1,000): notions kept, of which under half the activities visible")
    for m in (1000, 2000, 5000):
        p = [r for r in cons if int(r["covered_events"]) >= m]
        out.append(f"  m={m}: {len(p)}, {sum(r['vis'] < 0.5 for r in p)}")
    return "\n".join(out)


if __name__ == "__main__":
    main()
