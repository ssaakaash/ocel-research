#!/usr/bin/env python3
"""Self-check: the pandas distortion metrics in distortion.py must equal a plain-Python implementation on 6,000-event
slices of three real logs (Enron: fan-out, Bundestag: partitioned, Age of Empires II: many object types).

Compared per case notion: cases, flat rows, deficiency, convergence share, copies per event, largest activity inflation,
divergence share and variants per case; and per ordered type pair: U-objects, share of U-objects in several cases, mean
cases per U-object. Only dicts, sets and sorting are used, no pandas, so the two implementations share no code.

Run: realdata/.venv/bin/python -I realdata/src/check_distortion.py   (exits non-zero on the first mismatch)
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import distortion as D  # noqa: E402
from ocel_io import Ocel, load_ocel  # noqa: E402
from profile_all import DATASETS, LOAD_OPTIONS  # noqa: E402

SLICES = {"enron": (40000, 46000), "bundestag": (20000, 26000), "aoe2": (10000, 16000)}


def brute(o: Ocel) -> dict:
    n = len(o.events)
    act = dict(zip(o.events.eid, o.events.activity))
    ts = dict(zip(o.events.eid, o.events.timestamp))
    rel = {(e, x, t) for e, x, t in o.relations[["eid", "oid", "otype"]].itertuples(index=False)}
    types = sorted({t for _, _, t in rel})
    out = {"notions": {}, "coupling": {}}
    for t in types:
        rows = {(e, x) for e, x, tt in rel if tt == t}
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
        sig = collections.defaultdict(dict)                 # event -> other type -> sorted objects
        for e, x, tt in rel:
            if tt != t:
                sig[e].setdefault(tt, []).append(x)
        groups = collections.defaultdict(list)
        for e, x in rows:
            groups[(x, act[e])].append(e)
        repeated = {k: v for k, v in groups.items() if len(v) > 1}
        diverging = 0
        for evs in repeated.values():
            seen = collections.defaultdict(set)
            for e in evs:
                for tt, objs in sig[e].items():
                    seen[tt].add("|".join(sorted(objs)))
            diverging += any(len(s) > 1 for s in seen.values())
        has_other = any(tt != t for _, _, tt in rel)
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
        for u in types:
            if u == t:
                continue
            pairs = collections.defaultdict(set)
            by_event_t, by_event_u = collections.defaultdict(set), collections.defaultdict(set)
            for e, x, tt in rel:
                if tt == t:
                    by_event_t[e].add(x)
                elif tt == u:
                    by_event_u[e].add(x)
            for e, us in by_event_u.items():
                for xu in us:
                    pairs[xu] |= by_event_t.get(e, set())
            per_u = [len(v) for v in pairs.values() if v]
            if per_u:
                out["coupling"][(t, u)] = {"u_objects": len(per_u), "share_u_in_multiple_cases": round(sum(1 for c in per_u if c > 1) / len(per_u), 4),
                                           "mean_cases_per_u": round(sum(per_u) / len(per_u), 3)}
    return out


def main() -> None:
    checked = 0
    for key, (a, b) in SLICES.items():
        full = load_ocel(DATASETS[key], key, **LOAD_OPTIONS.get(key, {}))
        keep = set(full.events.sort_values(["timestamp", "eid"])["eid"].iloc[a:b])
        rels = full.relations[full.relations.eid.isin(keep)].reset_index(drop=True)
        o = Ocel(f"{key}_slice", full.events[full.events.eid.isin(keep)].reset_index(drop=True), full.objects[full.objects.oid.isin(set(rels.oid))].reset_index(drop=True), rels, full.o2o)
        fast, slow = D.analyse(o), brute(o)
        for c in fast["case_notions"]:
            for k, v in slow["notions"][c["case_type"]].items():
                if c[k] != v:
                    raise SystemExit(f"{key} / {c['case_type']}: {k} pandas={c[k]} plain={v}")
            checked += 1
        for c in fast["coupling"]:
            want = slow["coupling"].get((c["case_type"], c["other_type"]))
            if want is None or any(c[k] != v for k, v in want.items()):
                raise SystemExit(f"{key} / coupling {c['case_type']}->{c['other_type']}: pandas={c} plain={want}")
        print(f"{key}: {len(fast['case_notions'])} case notions and {len(fast['coupling'])} type pairs identical")
    print(f"distortion self-check passed: {checked} case notions identical on 3 real slices")


if __name__ == "__main__":
    main()
