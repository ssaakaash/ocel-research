#!/usr/bin/env python3
"""Self-check: the pandas distortion metrics in distortion.py must equal a plain-Python implementation.

Default: 6,000-event slices of three real logs (Enron: fan-out, Bundestag: partitioned, Age of Empires II: many object
types), recomputed with distortion.py. With --full: every one of the seven full logs (the Ethereum window as in the
study), compared with the published files in results/distortion/, and a summary is written to
results/check_distortion_full.json.

Compared per case notion: cases, flat rows, deficiency, convergence share, copies per event, largest activity inflation,
divergence share and variants per case; and per ordered type pair: U-objects, share of U-objects in several cases, mean
cases per U-object. Only dicts, sets and sorting are used, no pandas, so the two implementations share no code.

Run: realdata/.venv/bin/python -I realdata/src/check_distortion.py [--full]   (exits non-zero on the first mismatch)
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import distortion as D  # noqa: E402
from ocel_io import Ocel, load_ocel  # noqa: E402
from profile_all import DATASETS, LOAD_OPTIONS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SLICES = {"enron": (40000, 46000), "bundestag": (20000, 26000), "aoe2": (10000, 16000)}


def brute(o: Ocel) -> dict:
    n = len(o.events)
    act = dict(zip(o.events.eid, o.events.activity))
    ts = dict(zip(o.events.eid, o.events.timestamp))
    rel = {(e, x, t) for e, x, t in o.relations[["eid", "oid", "otype"]].itertuples(index=False)}
    types = sorted({t for _, _, t in rel})
    rows_of = collections.defaultdict(set)             # type -> {(event, object)}
    objs_of = collections.defaultdict(lambda: collections.defaultdict(set))   # type -> event -> objects
    for e, x, tt in rel:
        rows_of[tt].add((e, x))
        objs_of[tt][e].add(x)
    sig = collections.defaultdict(dict)                 # event -> type -> sorted objects joined
    for tt, by_event in objs_of.items():
        for e, xs in by_event.items():
            sig[e][tt] = "|".join(sorted(xs))
    out = {"notions": {}, "coupling": {}}
    for t in types:
        rows = rows_of[t]
        per_event = collections.defaultdict(set)
        for e, x in rows:
            per_event[e].add(x)
        covered = len(per_event)
        by_act_rows, by_act_events = collections.Counter(), collections.defaultdict(set)
        for e, x in rows:
            by_act_rows[act[e]] += 1
            by_act_events[act[e]].add(e)
        infl = max(by_act_rows[a] / len(by_act_events[a]) for a in by_act_rows)
        # divergence: (case, activity) pairs with >= 2 events; diverging if, for some other type, the object sets of those events differ
        groups = collections.defaultdict(list)
        for e, x in rows:
            groups[(x, act[e])].append(e)
        repeated = {k: v for k, v in groups.items() if len(v) > 1}
        diverging = 0
        for evs in repeated.values():
            seen = collections.defaultdict(set)
            for e in evs:
                for tt, objs in sig[e].items():
                    if tt != t:
                        seen[tt].add(objs)
            diverging += any(len(s) > 1 for s in seen.values())
        has_other = len(types) > 1
        divergence = round(diverging / len(repeated), 4) if (repeated and has_other and rows) else 0.0
        # variants
        by_case = collections.defaultdict(list)
        for e, x in rows:
            by_case[x].append(e)
        seqs = {x: tuple(act[e] for e in sorted(es, key=lambda e: (ts[e], e))) for x, es in by_case.items()}
        out["notions"][t] = {
            "cases": len(by_case), "flat_rows": len(rows), "deficiency": round(1 - covered / n, 4),
            "convergence_share": round(sum(1 for s in per_event.values() if len(s) > 1) / covered, 4),
            "copies_per_event": round(len(rows) / covered, 3), "max_activity_inflation": round(infl, 3),
            "divergence_share": divergence, "variants_per_case": round(len(set(seqs.values())) / len(seqs), 4),
        }
        by_event_t = objs_of[t]
        for u in types:
            if u == t:
                continue
            pairs = collections.defaultdict(set)
            for e, us in objs_of[u].items():
                ts_ = by_event_t.get(e, set())
                for xu in us:
                    pairs[xu] |= ts_
            per_u = [len(v) for v in pairs.values() if v]
            if per_u:
                out["coupling"][(t, u)] = {"u_objects": len(per_u), "share_u_in_multiple_cases": round(sum(1 for c in per_u if c > 1) / len(per_u), 4),
                                           "mean_cases_per_u": round(sum(per_u) / len(per_u), 3)}
    return out


def compare(key: str, fast: dict, slow: dict) -> int:
    for c in fast["case_notions"]:
        for k, v in slow["notions"][c["case_type"]].items():
            if c[k] != v:
                raise SystemExit(f"{key} / {c['case_type']}: {k} pandas={c[k]} plain={v}")
    for c in fast["coupling"]:
        want = slow["coupling"].get((c["case_type"], c["other_type"]))
        if want is None or any(c[k] != v for k, v in want.items()):
            raise SystemExit(f"{key} / coupling {c['case_type']}->{c['other_type']}: pandas={c} plain={want}")
    print(f"{key}: {len(fast['case_notions'])} case notions and {len(fast['coupling'])} type pairs identical", flush=True)
    return len(fast["case_notions"])


def main() -> None:
    checked = 0
    if "--full" in sys.argv[1:]:
        res = ROOT / "results"
        summary = {}
        for key, path in DATASETS.items():
            published = json.loads((res / "distortion" / f"{key}.json").read_text())
            n = compare(key, published, brute(load_ocel(path, key, **LOAD_OPTIONS.get(key, {}))))
            summary[key] = {"case_notions": n, "type_pairs": len(published["coupling"])}
            checked += n
        (res / "check_distortion_full.json").write_text(json.dumps({"identical": True, "logs": summary}, indent=2) + "\n")
        print(f"distortion full-log check passed: {checked} case notions identical on 7 full logs")
        return
    for key, (a, b) in SLICES.items():
        full = load_ocel(DATASETS[key], key, **LOAD_OPTIONS.get(key, {}))
        keep = set(full.events.sort_values(["timestamp", "eid"])["eid"].iloc[a:b])
        rels = full.relations[full.relations.eid.isin(keep)].reset_index(drop=True)
        o = Ocel(f"{key}_slice", full.events[full.events.eid.isin(keep)].reset_index(drop=True), full.objects[full.objects.oid.isin(set(rels.oid))].reset_index(drop=True), rels, full.o2o)
        checked += compare(key, D.analyse(o), brute(o))
    print(f"distortion self-check passed: {checked} case notions identical on 3 real slices")


if __name__ == "__main__":
    main()
