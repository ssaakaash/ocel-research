"""Controlled violation injection for predicates with too few natural positives.

The oracle is always the predicate evaluated on the *mutated native log*; no label file exists, so
detector/label leakage is impossible by construction. Mutations are template-specific and minimal.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from cooc import Predicate, _acts, native_view
from ocel_io import Ocel

MIN_POSITIVES = 5


def _clone(ocel: Ocel) -> Ocel:
    return Ocel(ocel.name, ocel.events.copy(), ocel.objects.copy(), ocel.relations.copy(), ocel.o2o.copy())


def _set_ts(o: Ocel, eid: str, ts: pd.Timestamp) -> None:
    o.events.loc[o.events["eid"] == eid, "timestamp"] = ts
    o.relations.loc[o.relations["eid"] == eid, "timestamp"] = ts


def inject(ocel: Ocel, pred: Predicate, n: int, seed: int) -> tuple[Ocel, int]:
    """Return (mutated log, number of scope objects mutated)."""
    rng = np.random.default_rng(seed)
    o = _clone(ocel)
    v = native_view(o)
    p, scope = pred.params, pred.scope
    done = 0
    if pred.template == "PREC":
        ev = v.events_of(scope)
        first_t = ev[ev["activity"].isin(_acts(p["first"]))].groupby("oid")["timestamp"].min()
        then = ev[ev["activity"].isin(_acts(p["then"]))].sort_values("timestamp").groupby("oid").first()
        cand = [s for s in then.index if s in first_t.index and then.loc[s, "timestamp"] >= first_t[s]]
        for s in rng.permutation(cand)[:n]:
            _set_ts(o, then.loc[s, "eid"], first_t[s] - pd.Timedelta(hours=1)); done += 1
    elif pred.template == "SODA":
        ev = v.events_of(scope)
        a = ev[ev["activity"].isin(_acts(p["a"]))].dropna(subset=[p["attr_a"]]).groupby("oid").first()
        b = ev[ev["activity"].isin(_acts(p["b"]))].dropna(subset=[p["attr_b"]]).groupby("oid").first()
        cand = [s for s in a.index if s in b.index and a.loc[s, p["attr_a"]] != b.loc[s, p["attr_b"]]]
        for s in rng.permutation(cand)[:n]:
            o.events.loc[o.events["eid"] == b.loc[s, "eid"], p["attr_b"]] = a.loc[s, p["attr_a"]]; done += 1
    elif pred.template == "SODO":
        s_rel = o.relations[o.relations["otype"] == scope][["eid", "oid"]].rename(columns={"oid": "s"})
        r_rel = o.relations[o.relations["otype"] == p["resource"]][["eid", "oid"]].rename(columns={"oid": "r"})
        ev = o.events[["eid", "activity"]]
        sr = s_rel.merge(r_rel, on="eid").merge(ev, on="eid")
        a = sr[sr["activity"].isin(_acts(p["a"]))].groupby("s").first()
        b_ev = s_rel.merge(ev, on="eid")
        b_ev = b_ev[b_ev["activity"].isin(_acts(p["b"]))].groupby("s").first()
        cand = [s for s in a.index if s in b_ev.index]
        new_rows = []
        for s in rng.permutation(cand)[:n]:
            new_rows.append({"eid": b_ev.loc[s, "eid"], "oid": a.loc[s, "r"], "qualifier": None, "activity": b_ev.loc[s, "activity"],
                             "timestamp": pd.NaT, "otype": p["resource"]}); done += 1
        if new_rows:
            o.relations = pd.concat([o.relations, pd.DataFrame(new_rows)], ignore_index=True)
    elif pred.template == "STALL":
        ev = v.events_of(scope)
        delta = pd.Timedelta(days=p["days"])
        a_t = ev[ev["activity"].isin(_acts(p["a"]))].groupby("oid")["timestamp"].min()
        b = ev[ev["activity"].isin(_acts(p["then"]))]
        cand = [s for s in a_t.index if a_t[s] + delta < v.log_end and (b["oid"] == s).any()]
        for s in rng.permutation(cand)[:n]:
            drop = b[b["oid"] == s]["eid"]
            o.relations = o.relations[~((o.relations["oid"] == s) & (o.relations["eid"].isin(drop)))]; done += 1
    elif pred.template == "REPEAT":
        ev = v.events_of(scope)
        a = ev[ev["activity"].isin(_acts(p["a"]))].sort_values("timestamp").groupby("oid").first()
        new_ev, new_rel = [], []
        for i, s in enumerate(rng.permutation(list(a.index))[: n]):
            eid = a.loc[s, "eid"]
            for extra in range(p["k"]):
                nid = f"{eid}#dup{i}_{extra}"
                row = o.events[o.events["eid"] == eid].iloc[0].copy(); row["eid"] = nid
                row["timestamp"] = row["timestamp"] + pd.Timedelta(minutes=1 + extra)
                new_ev.append(row)
                r = o.relations[o.relations["eid"] == eid].copy(); r["eid"] = nid; new_rel.append(r)
            done += 1
        if new_ev:
            o.events = pd.concat([o.events, pd.DataFrame(new_ev)], ignore_index=True)
            o.relations = pd.concat([o.relations] + new_rel, ignore_index=True)
    elif pred.template == "CLOSURE":
        t = v.obj_type
        pairs = pd.concat([o.o2o.rename(columns={"oid": "s", "oid_2": "c"}), o.o2o.rename(columns={"oid_2": "s", "oid": "c"})])
        pairs = pairs[(pairs["s"].map(t) == scope) & (pairs["c"].map(t) == p["child"])]
        c_ev = v.events_of(p["child"])
        c_ev = c_ev[c_ev["activity"].isin(_acts(p["child_act"]))]
        have = set(c_ev["oid"])
        cand = pairs[pairs["c"].isin(have)]
        for _, row in cand.sample(frac=1.0, random_state=int(seed)).head(n).iterrows():
            drop = c_ev[c_ev["oid"] == row["c"]]["eid"]
            o.relations = o.relations[~((o.relations["oid"] == row["c"]) & (o.relations["eid"].isin(drop)))]; done += 1
    elif pred.template == "DEADLINE":
        pass  # natural prevalence only; deadlines are object attributes
    elif pred.template == "AFTER":
        ev = v.events_of(scope)
        fin = ev[ev["activity"].isin(_acts(p["final"]))].groupby("oid")["timestamp"].min()
        late = ev[ev["activity"].isin(_acts(p["late"]))].sort_values("timestamp").groupby("oid").first()
        cand = [s for s in late.index if s in fin.index and late.loc[s, "timestamp"] <= fin[s]]
        for s in rng.permutation(cand)[:n]:
            _set_ts(o, late.loc[s, "eid"], fin[s] + pd.Timedelta(hours=1)); done += 1
    # LOAD: no injection; relies on the data-adaptive threshold
    return o, done
