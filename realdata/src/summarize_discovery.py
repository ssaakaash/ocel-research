#!/usr/bin/env python3
"""Combine results/discovery/*.json into discovery_by_notion.csv and discovery_summary.json.

Case notions whose mining did not finish (time budget, or the child process failed) are listed with the reason, not scored. The summary relates the discovered models to the distortion metrics across the analysed case notions (Spearman rho
over notions): loop share, fitness and precision against divergence share, copies per event and coverage.

Run: python3 -I realdata/src/summarize_discovery.py   (standard library only)
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

RES = Path(__file__).resolve().parents[1] / "results"
FIELDS = ["log", "case_type", "cases", "flat_rows", "fitness", "precision", "loop_share", "tree_nodes", "arcs",
          "activity_coverage", "divergence_share", "copies_per_event", "coverage", "act_visible_share"]


def ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a: list[float], b: list[float]) -> float | None:
    if len(a) < 3:
        return None
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return round(num / den, 4) if den else None


def main() -> None:
    with (RES / "consequence_by_notion.csv").open(encoding="utf-8") as h:
        cons = {(r["log"], r["case_type"]): r for r in csv.DictReader(h)}
    rows, unfinished = [], []
    for f in sorted((RES / "discovery").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        dist = {c["case_type"]: c for c in json.loads((RES / "distortion" / f.name).read_text(encoding="utf-8"))["case_notions"]}
        for n in d["notions"]:
            if not n.get("completed", True):
                unfinished.append(f"{d['log']}/{n['case_type']} ({n.get('stopped_by', 'time budget or failure')})")
                continue
            c = dist[n["case_type"]]
            rows.append({**{k: n[k] for k in ("case_type", "cases", "flat_rows", "fitness", "precision", "loop_share", "tree_nodes", "arcs", "activity_coverage")},
                         "log": d["log"], "divergence_share": c["divergence_share"], "copies_per_event": c["copies_per_event"],
                         "coverage": round(1 - c["deficiency"], 4), "act_visible_share": float(cons[(d["log"], n["case_type"])]["act_visible_share"])})
    with (RES / "discovery_by_notion.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, FIELDS)
        w.writeheader()
        w.writerows(rows)
    prec = [r for r in rows if r["precision"] is not None]
    corr = {}
    for m in ("loop_share", "fitness", "precision", "tree_nodes"):
        sub = prec if m == "precision" else [r for r in rows if r[m] is not None]
        for x in ("divergence_share", "copies_per_event", "coverage"):
            corr[f"{m}~{x}"] = {"rho": spearman([r[m] for r in sub], [r[x] for r in sub]), "notions": len(sub)}
    summary = {
        "notions": len(rows), "not_completed": unfinished,
        "fitness_median": statistics.median(r["fitness"] for r in rows), "fitness_min": min(r["fitness"] for r in rows),
        "precision_computed": len(prec),
        "precision_median": statistics.median(r["precision"] for r in prec) if prec else None,
        "precision_min": min(r["precision"] for r in prec) if prec else None,
        "loop_share_ge_0.9": sum(r["loop_share"] is not None and r["loop_share"] >= 0.9 for r in rows),
        "model_covers_under_half_of_activities": sum(r["activity_coverage"] < 0.5 for r in rows),
        "high_divergence_notions": sum(r["divergence_share"] >= 0.5 for r in rows),
        "high_divergence_with_loop_share_ge_0.9": sum(r["divergence_share"] >= 0.5 and r["loop_share"] is not None and r["loop_share"] >= 0.9 for r in rows),
        "low_divergence_with_loop_share_ge_0.9": sum(r["divergence_share"] < 0.5 and r["loop_share"] is not None and r["loop_share"] >= 0.9 for r in rows),
        "spearman": corr,
    }
    (RES / "discovery_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
