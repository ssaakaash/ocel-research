#!/usr/bin/env python3
"""Predicate-free flattening-distortion metrics for real object-centric event logs.

For every log and every case notion T (flatten on object type T):
  deficiency            share of events with no T-object (dropped)
  convergence_share     share of covered events related to >= 2 T-objects (copied to several cases)
  copies_per_event      flat rows / covered events (count inflation of event frequencies)
  divergence_share      share of (case, activity) pairs with >=2 events whose other-object sets differ
  nested_children       other types U that are *exclusive* to a case (>= 95 % of U-objects occur in one T-case), have own multi-event lifecycles (>= 2 events per object)
                        and have fan-out >= 1.5 per case: true 1:N sub-instances (items of an order)
  cross_instance_adjacency
                        among directly-follows pairs in cases with >= 2 nested-child objects, the share whose two
                        events concern disjoint child objects: adjacent in the flat log, unrelated in the data
For every ordered type pair (T, U) the object-level coupling is also reported:
  share of U-objects touching >= 2 T-objects, and mean degree.

Run: realdata/.venv/bin/python -I realdata/src/distortion.py [log ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocel_io import Ocel, flattening_stats, load_ocel  # noqa: E402
from profile_all import DATASETS, LOAD_OPTIONS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "distortion"
EXCLUSIVE, FANOUT = 0.95, 1.5


def pair_table(rel: pd.DataFrame, t: str, u: str) -> pd.DataFrame:
    a = rel[rel["otype"] == t][["eid", "oid"]].rename(columns={"oid": "t"})
    b = rel[rel["otype"] == u][["eid", "oid"]].rename(columns={"oid": "u"})
    return a.merge(b, on="eid")[["t", "u"]].drop_duplicates()


def coupling(rel: pd.DataFrame, t: str, u: str) -> dict | None:
    p = pair_table(rel, t, u)
    if p.empty:
        return None
    per_u = p.groupby("u")["t"].nunique()
    per_t = p.groupby("t")["u"].nunique()
    return {
        "case_type": t, "other_type": u,
        "u_objects": int(len(per_u)), "share_u_in_multiple_cases": round(float((per_u > 1).mean()), 4),
        "mean_cases_per_u": round(float(per_u.mean()), 3),
        "t_cases": int(len(per_t)), "mean_u_per_case": round(float(per_t.mean()), 3), "max_u_per_case": int(per_t.max()),
    }


def cross_instance_adjacency(ocel: Ocel, rel: pd.DataFrame, t: str, children: list[str]) -> dict:
    cases = rel[rel["otype"] == t][["eid", "oid"]].drop_duplicates()
    flat = cases.merge(ocel.events[["eid", "timestamp"]], on="eid").sort_values(["oid", "timestamp", "eid"], kind="stable")
    flat["next_eid"] = flat.groupby("oid")["eid"].shift(-1)
    pairs = flat.dropna(subset=["next_eid"])[["oid", "eid", "next_eid"]]
    if pairs.empty:
        return {"pairs": 0}
    child_sets = {}
    for u in children:
        r = rel[rel["otype"] == u][["eid", "oid"]]
        child_sets[u] = r.groupby("eid")["oid"].agg(frozenset).to_dict()
        n_children = r.merge(cases, on="eid").groupby("oid_y")["oid_x"].nunique()
        eligible = set(n_children[n_children >= 2].index)
        child_sets[u + "#eligible"] = eligible
    eligible_pairs = cross = 0
    for case, e1, e2 in pairs.itertuples(index=False):
        hit = elig = False
        for u in children:
            if case not in child_sets[u + "#eligible"]:
                continue
            elig = True
            s1, s2 = child_sets[u].get(e1), child_sets[u].get(e2)
            if s1 and s2 and s1.isdisjoint(s2):
                hit = True
                break
        eligible_pairs += elig
        cross += hit
    return {"pairs": int(len(pairs)), "eligible_pairs": int(eligible_pairs), "cross_instance_pairs": int(cross),
            "cross_instance_adjacency": round(cross / eligible_pairs, 4) if eligible_pairs else None}


def variant_stats(ocel: Ocel, rel: pd.DataFrame, t: str) -> dict:
    """Distinct activity sequences (variants) per flat(T): the analyst-facing symptom of interleaved sub-instances."""
    cases = rel[rel["otype"] == t][["eid", "oid"]].drop_duplicates()
    flat = cases.merge(ocel.events[["eid", "activity", "timestamp"]], on="eid").sort_values(["oid", "timestamp", "eid"], kind="stable")
    seqs = flat.groupby("oid")["activity"].agg(tuple)
    n = len(seqs)
    return {"variants": int(seqs.nunique()), "variants_per_case": round(seqs.nunique() / n, 4) if n else None,
            "median_case_length": float(seqs.map(len).median()) if n else None}


def analyse(ocel: Ocel) -> dict:
    rel = ocel.relations[["eid", "oid", "otype"]].drop_duplicates()
    n_events = len(ocel.events)
    types = sorted(ocel.object_types)
    report = {"log": ocel.name, "events": int(n_events), "objects": int(len(ocel.objects)), "object_types": types,
              "e2o_rows": int(len(rel)), "objects_per_event_mean": round(len(rel) / n_events, 3), "case_notions": [], "coupling": []}
    for t in types:
        rows_t = rel[rel["otype"] == t]
        covered = rows_t["eid"].nunique()
        per_event = rows_t.groupby("eid")["oid"].nunique()
        act = ocel.events[["eid", "activity"]].merge(rows_t[["eid", "oid"]], on="eid")
        infl = (act.groupby("activity")["eid"].size() / act.groupby("activity")["eid"].nunique())
        fs = flattening_stats(ocel, t)
        entry = {
            "case_type": t, "cases": int(rows_t["oid"].nunique()), "flat_rows": int(len(rows_t.drop_duplicates())),
            "deficiency": round(1 - covered / n_events, 4), "convergence_share": round(float((per_event > 1).mean()), 4),
            "copies_per_event": round(len(rows_t.drop_duplicates()) / covered, 3),
            "max_activity_inflation": round(float(infl.max()), 3), "divergence_share": fs["divergence_share"],
        }
        kids = []
        for u in types:
            if u == t:
                continue
            c = coupling(rel, t, u)
            if c is None:
                continue
            report["coupling"].append(c)
            p = pair_table(rel, t, u)
            excl = float((p.groupby("u")["t"].nunique() <= 1).mean())
            events_per_u = float(rel[rel["otype"] == u].groupby("oid").size().mean())
            c["events_per_other_object"] = round(events_per_u, 3)
            # a nested child must have its own multi-event lifecycle (items of an order), not be a mere event identifier
            if excl >= EXCLUSIVE and c["mean_u_per_case"] >= FANOUT and events_per_u >= 2.0:
                kids.append(u)
        entry["nested_children"] = kids
        entry.update(variant_stats(ocel, rel, t))
        entry.update(cross_instance_adjacency(ocel, rel, t, kids) if kids else {"cross_instance_adjacency": None})
        report["case_notions"].append(entry)
    return report


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = set(sys.argv[1:]) or set(DATASETS)
    for key, path in DATASETS.items():
        if key not in wanted or not Path(path).exists():
            continue
        rep = analyse(load_ocel(path, key, **LOAD_OPTIONS.get(key, {})))
        (OUT / f"{key}.json").write_text(json.dumps(rep, indent=2, default=str))
        print(f"\n=== {key}: events={rep['events']:,} e2o/event={rep['objects_per_event_mean']}")
        for c in rep["case_notions"]:
            print(f"  flat[{c['case_type']:13s}] def={c['deficiency']:.3f} conv={c['convergence_share']:.3f} copies={c['copies_per_event']:7.3f} "
                  f"maxActInfl={c['max_activity_inflation']:7.3f} div={c['divergence_share']:.3f} var/case={c['variants_per_case']} kids={c['nested_children']} CAS={c.get('cross_instance_adjacency')}")
        shared = [c for c in rep["coupling"] if c["share_u_in_multiple_cases"] > 0.5]
        for c in sorted(shared, key=lambda x: -x["share_u_in_multiple_cases"])[:6]:
            print(f"  coupling {c['other_type']:>12s} objs in >=2 {c['case_type']} cases: {c['share_u_in_multiple_cases']:.2f} (mean {c['mean_cases_per_u']})")


if __name__ == "__main__":
    main()
