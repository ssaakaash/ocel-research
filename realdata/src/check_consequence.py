#!/usr/bin/env python3
"""Self-check: the vectorised directly-follows pairs and entity counts in consequence.py must equal a plain-Python
implementation on a 6,000-event slice of the real Enron log (many timestamp ties, many-to-many relations).

Run: realdata/.venv/bin/python -I realdata/src/check_consequence.py   (exits non-zero on mismatch)
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consequence as C  # noqa: E402
from ocel_io import Ocel, load_ocel  # noqa: E402
from profile_all import DATASETS, LOAD_OPTIONS  # noqa: E402


def main() -> None:
    full = load_ocel(DATASETS["enron"], "enron", **LOAD_OPTIONS["enron"])
    keep = set(full.events.sort_values(["timestamp", "eid"])["eid"].iloc[40000:46000])
    o = Ocel("enron_slice", full.events[full.events.eid.isin(keep)].reset_index(drop=True), full.objects,
             full.relations[full.relations.eid.isin(keep)].reset_index(drop=True), full.o2o)
    P = C.Prepared(o)
    ts = dict(zip(o.events.eid, o.events.timestamp))
    eid_of = dict(enumerate(sorted(o.events.eid)))
    for t in sorted(o.relations.otype.unique()):
        rows = o.relations[o.relations.otype == t][["eid", "oid"]].drop_duplicates()
        by_case = collections.defaultdict(list)
        for e, c in rows.itertuples(index=False):
            by_case[c].append(e)
        brute = []
        for es in by_case.values():
            es = sorted(es, key=lambda e: (ts[e], e))
            brute += list(zip(es[:-1], es[1:]))
        e1, e2 = P.pairs(t)
        fast = sorted((eid_of[a], eid_of[b]) for a, b in zip(e1, e2))
        if fast != sorted(brute):
            raise SystemExit(f"directly-follows mismatch for case notion {t}")
    t, u = "EMAILADDRESS:TO", "EMAILADDRESS:FROM"
    n_t = o.relations[o.relations.otype == t].groupby("eid").oid.nunique()
    ru = o.relations[o.relations.otype == u][["eid", "oid"]].drop_duplicates()
    true_cnt = ru.groupby("oid").size()
    flat = collections.Counter()
    for e, x in ru.itertuples(index=False):
        flat[x] += int(n_t.get(e, 0))
    a, b = true_cnt.to_numpy(float), np.array([flat[x] for x in true_cnt.index], float)
    res = C.analyse("enron_slice", o, {})
    got = next(x for n in res["notions"] if n["case_type"] == t for x in n["C4_entity_rankings"] if x["entity_type"] == u)
    if C.spearman(a, b) != got["rho"] or round(float((b == 0).mean()), 4) != got["objects_invisible_share"]:
        raise SystemExit("entity-ranking mismatch")
    print("consequence self-check passed: DF pairs identical for", len(o.relations.otype.unique()), "case notions; entity ranking identical")


if __name__ == "__main__":
    main()
