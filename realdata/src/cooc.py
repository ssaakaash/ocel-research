"""Executable Cross-Object Observability Coverage (COOC).

A *view* is what an analyst can see in a given representation:
    native   the full OCEL (event-to-object relations of every type, object-to-object links)
    flat     case-centric flattening on one object type: one row per (event, case object),
             only event attributes survive (pm4py ``ocel_flattening`` semantics)
    leading  flattening on a leading type that also pulls in events of declared child types
             reached through object-to-object links (the strong "expert-built" baseline);
             identities of the child objects are lost

A *predicate* is an instance of a template (PREC, SODO, SODA, LOAD, CLOSURE, STALL, REPEAT) with
declared requirements (object types, event attributes, activities, o2o). For every view:
    not expressible   a requirement is missing from the view
    correct           the flagged scope objects equal the native oracle exactly
    silent error      expressible, but the flagged set differs from the oracle
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ocel_io import Ocel


@dataclass
class View:
    name: str
    kind: str
    ev: pd.DataFrame           # eid, activity, timestamp, + event attributes
    rel: pd.DataFrame          # eid, oid, otype
    types: set
    attrs: set
    has_o2o: bool
    activities: set
    o2o: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=["oid", "oid_2"]))
    obj_type: dict = field(default_factory=dict)
    log_end: pd.Timestamp | None = None
    case_type: str = "*"
    objattrs: pd.DataFrame | None = None

    def events_of(self, scope: str) -> pd.DataFrame:
        """Events directly related to objects of type ``scope`` -> (oid, eid, activity, timestamp, ...)."""
        r = self.rel[self.rel["otype"] == scope][["eid", "oid"]]
        return r.merge(self.ev, on="eid", how="inner")


def _event_attr_columns(ocel: Ocel) -> set:
    cols = [c for c in ocel.events.columns if c not in ("eid", "activity", "timestamp")]
    return {c for c in cols if ocel.events[c].notna().any()}


def native_view(ocel: Ocel) -> View:
    rel = ocel.relations[["eid", "oid", "otype"]].drop_duplicates()
    return View(ocel.name + ":native", "native", ocel.events, rel, set(ocel.object_types), _event_attr_columns(ocel),
                len(ocel.o2o) > 0, set(ocel.events["activity"]), ocel.o2o[["oid", "oid_2"]] if len(ocel.o2o) else pd.DataFrame(columns=["oid", "oid_2"]),
                dict(zip(ocel.objects["oid"], ocel.objects["type"])), ocel.events["timestamp"].max(),
                objattrs=ocel.objects.set_index("oid"))


def flat_view(ocel: Ocel, case_type: str) -> View:
    rel = ocel.relations[ocel.relations["otype"] == case_type][["eid", "oid"]].drop_duplicates()
    flat = rel.merge(ocel.events, on="eid", how="left")
    flat["eid"] = flat["eid"] + "||" + flat["oid"]
    rel2 = flat[["eid", "oid"]].assign(otype=case_type)
    ev = flat.drop(columns=["oid"])
    return View(f"{ocel.name}:flat[{case_type}]", "flat", ev, rel2, {case_type}, _event_attr_columns(ocel), False,
                set(ev["activity"]), obj_type={o: case_type for o in rel["oid"].unique()}, log_end=ocel.events["timestamp"].max(), case_type=case_type)


def dflat_view(ocel: Ocel, case_type: str) -> View:
    """Denormalised flat log: case = ``case_type`` object; the ids of every other related object are
    kept as list-valued attributes of the event copy (best-case practitioner export).
    Events are still copied once per case object (convergence) and o2o links / object attributes are lost."""
    cases = ocel.relations[ocel.relations["otype"] == case_type][["eid", "oid"]].drop_duplicates().rename(columns={"oid": "case"})
    others = ocel.relations[ocel.relations["otype"] != case_type][["eid", "oid", "otype"]].drop_duplicates()
    case_rows = cases.assign(oid=cases["case"], otype=case_type)
    attr_rows = cases.merge(others, on="eid")
    rel = pd.concat([case_rows[["eid", "case", "oid", "otype"]], attr_rows[["eid", "case", "oid", "otype"]]], ignore_index=True)
    rel["eid"] = rel["eid"] + "||" + rel["case"]
    ev = cases.merge(ocel.events, on="eid", how="left")
    ev["eid"] = ev["eid"] + "||" + ev["case"]
    ev = ev.drop(columns=["case"])
    types = set(rel["otype"].unique())
    return View(f"{ocel.name}:dflat[{case_type}]", "dflat", ev, rel[["eid", "oid", "otype"]], types, _event_attr_columns(ocel), False,
                set(ev["activity"]), obj_type=dict(zip(ocel.objects["oid"], ocel.objects["type"])), log_end=ocel.events["timestamp"].max(), case_type=case_type)


def leading_view(ocel: Ocel, case_type: str, children: list[str]) -> View:
    """Leading-type flattening that includes events of ``children`` objects linked by o2o."""
    direct = ocel.relations[ocel.relations["otype"] == case_type][["eid", "oid"]]
    t = dict(zip(ocel.objects["oid"], ocel.objects["type"]))
    o = ocel.o2o[["oid", "oid_2"]]
    pairs = pd.concat([o.rename(columns={"oid": "s", "oid_2": "c"}), o.rename(columns={"oid_2": "s", "oid": "c"})])
    pairs = pairs[(pairs["s"].map(t) == case_type) & (pairs["c"].map(t).isin(children))]
    child_ev = ocel.relations[ocel.relations["otype"].isin(children)][["eid", "oid"]].rename(columns={"oid": "c"}).merge(pairs, on="c")[["eid", "s"]].rename(columns={"s": "oid"})
    rel = pd.concat([direct, child_ev]).drop_duplicates()
    flat = rel.merge(ocel.events, on="eid", how="left")
    flat["eid"] = flat["eid"] + "||" + flat["oid"]
    rel2 = flat[["eid", "oid"]].assign(otype=case_type)
    ev = flat.drop(columns=["oid"])
    return View(f"{ocel.name}:leading[{case_type}+{'/'.join(children)}]", "leading", ev, rel2, {case_type}, _event_attr_columns(ocel), False,
                set(ev["activity"]), obj_type={o_: case_type for o_ in rel["oid"].unique()}, log_end=ocel.events["timestamp"].max(), case_type=case_type)


# ----------------------------------------------------------------------------- predicates

@dataclass
class Predicate:
    pid: str
    family: str
    template: str
    scope: str
    params: dict
    rationale: str
    req_types: set = field(default_factory=set)
    req_attrs: set = field(default_factory=set)
    req_acts: set = field(default_factory=set)
    req_o2o: bool = False
    req_objattrs: set = field(default_factory=set)

    def expressible(self, v: View) -> tuple[bool, str]:
        if not self.req_types <= v.types:
            return False, f"missing object type(s): {sorted(self.req_types - v.types)}"
        if not self.req_attrs <= v.attrs:
            return False, f"missing event attribute(s): {sorted(self.req_attrs - v.attrs)}"
        if not self.req_acts <= v.activities:
            return False, f"activity absent in view: {sorted(self.req_acts - v.activities)}"
        if self.req_o2o and not (v.has_o2o or v.kind in ("leading",)):
            return False, "object-to-object links unavailable"
        if self.req_objattrs and (v.objattrs is None or not self.req_objattrs <= set(v.objattrs.columns)):
            return False, f"object attribute(s) unavailable: {sorted(self.req_objattrs)}"
        return True, ""

    def evaluate(self, v: View) -> set:
        return TEMPLATES[self.template](v, self.scope, self.params)


def _acts(x) -> list:
    return [x] if isinstance(x, str) else list(x)


def _ns(s: pd.Series) -> np.ndarray:
    """Timestamps as int64 nanoseconds regardless of pandas datetime resolution/timezone."""
    return pd.to_datetime(s, utc=True).dt.tz_localize(None).to_numpy("datetime64[ns]").astype(np.int64)


def make_predicate(pid: str, family: str, template: str, scope: str, rationale: str, **params) -> Predicate:
    """Build a predicate and derive its requirements from the template parameters."""
    types, attrs, acts, o2o = {scope}, set(), set(), False
    for key in ("a", "b", "first", "then", "open", "close", "scope_act", "child_act", "final", "late", "act"):
        if key in params:
            acts |= set(_acts(params[key]))
    if template == "SODO":
        types.add(params["resource"])
    if template == "SODA":
        attrs |= {params["attr_a"], params["attr_b"]}
    if template == "LOAD":
        types.add(params["item"])
        # the resource type is the scope; the open/close activities must be visible
    if template == "CLOSURE":
        types.add(params["child"]); o2o = True
    objattrs = {params["attr"]} if template == "DEADLINE" else set()
    if template == "DEADLINE":
        types.add(params["type"])
    return Predicate(pid, family, template, scope, params, rationale, types, attrs, acts, o2o, objattrs)


def t_prec(v: View, scope: str, p: dict) -> set:
    ev = v.events_of(scope)
    first, then = _acts(p["first"]), _acts(p["then"])
    ts_first = ev[ev["activity"].isin(first)].groupby("oid")["timestamp"].min().rename("t_first")
    b = ev[ev["activity"].isin(then)][["oid", "timestamp"]].merge(ts_first, on="oid", how="left")
    bad = b[b["t_first"].isna() | (b["timestamp"] < b["t_first"])]
    return set(bad["oid"])


def t_soda(v: View, scope: str, p: dict) -> set:
    ev = v.events_of(scope)
    a = ev[ev["activity"].isin(_acts(p["a"]))][["oid", p["attr_a"]]].dropna().rename(columns={p["attr_a"]: "val"})
    b = ev[ev["activity"].isin(_acts(p["b"]))][["oid", p["attr_b"]]].dropna().rename(columns={p["attr_b"]: "val"})
    both = a.merge(b, on=["oid", "val"])
    return set(both["oid"])


def t_sodo(v: View, scope: str, p: dict) -> set:
    s_rel = v.rel[v.rel["otype"] == scope][["eid", "oid"]].rename(columns={"oid": "s"})
    r_rel = v.rel[v.rel["otype"] == p["resource"]][["eid", "oid"]].rename(columns={"oid": "r"})
    ev = v.ev[["eid", "activity"]]
    sr = s_rel.merge(r_rel, on="eid").merge(ev, on="eid")
    a = sr[sr["activity"].isin(_acts(p["a"]))][["s", "r"]].drop_duplicates()
    b = sr[sr["activity"].isin(_acts(p["b"]))][["s", "r"]].drop_duplicates()
    return set(a.merge(b, on=["s", "r"])["s"])


def load_peaks(v: View, scope: str, p: dict) -> dict:
    """Peak number of simultaneously open items per resource (scope = resource type)."""
    item = p["item"]
    res = v.rel[v.rel["otype"] == scope][["eid", "oid"]].rename(columns={"oid": "r"})
    its = v.rel[v.rel["otype"] == item][["eid", "oid"]].rename(columns={"oid": "i"})
    ev = v.ev[["eid", "activity", "timestamp"]]
    opens = res.merge(its, on="eid").merge(ev, on="eid")
    opens = opens[opens["activity"].isin(_acts(p["open"]))].groupby(["r", "i"])["timestamp"].min().reset_index().rename(columns={"timestamp": "t0"})
    closes = its.merge(ev, on="eid")
    closes = closes[closes["activity"].isin(_acts(p["close"]))].groupby("i")["timestamp"].min().rename("t1")
    iv = opens.merge(closes, on="i", how="left")
    far = (v.log_end or iv["t0"].max()) + pd.Timedelta(days=1)
    iv["t1"] = iv["t1"].fillna(far)
    iv = iv[iv["t1"] >= iv["t0"]]
    peaks = {}
    for r, g in iv.groupby("r"):
        pts = np.concatenate([np.column_stack([_ns(g["t0"]), np.ones(len(g), dtype=np.int64)]),
                              np.column_stack([_ns(g["t1"]), -np.ones(len(g), dtype=np.int64)])])
        order = np.lexsort((pts[:, 1], pts[:, 0]))  # closes before opens at equal time
        peaks[r] = int(np.cumsum(pts[order, 1]).max())
    return peaks


def t_load(v: View, scope: str, p: dict) -> set:
    """Flag resources (scope type) whose peak number of simultaneously open items exceeds k."""
    return {r for r, peak in load_peaks(v, scope, p).items() if peak > p["k"]}


def t_closure(v: View, scope: str, p: dict) -> set:
    """For scope s with a ``scope_act`` event at time t, every o2o child of type ``child`` must have a ``child_act`` event at or before t."""
    t = v.obj_type
    o = v.o2o
    pairs = pd.concat([o.rename(columns={"oid": "s", "oid_2": "c"}), o.rename(columns={"oid_2": "s", "oid": "c"})])
    pairs = pairs[(pairs["s"].map(t) == scope) & (pairs["c"].map(t) == p["child"])].drop_duplicates()
    s_ev = v.events_of(scope)
    s_ev = s_ev[s_ev["activity"].isin(_acts(p["scope_act"]))].groupby("oid")["timestamp"].min().rename("t_s").reset_index().rename(columns={"oid": "s"})
    c_ev = v.events_of(p["child"])
    c_ev = c_ev[c_ev["activity"].isin(_acts(p["child_act"]))].groupby("oid")["timestamp"].min().rename("t_c").reset_index().rename(columns={"oid": "c"})
    m = pairs.merge(s_ev, on="s").merge(c_ev, on="c", how="left")
    bad = m[m["t_c"].isna() | (m["t_c"] > m["t_s"])]
    return set(bad["s"])


def t_stall(v: View, scope: str, p: dict) -> set:
    ev = v.events_of(scope)
    delta = pd.Timedelta(days=p["days"])
    a = ev[ev["activity"].isin(_acts(p["a"]))].groupby("oid")["timestamp"].min().rename("t_a")
    after = ev[ev["activity"].isin(_acts(p["then"]))].groupby("oid")["timestamp"].max().rename("t_b")
    m = pd.concat([a, after], axis=1).dropna(subset=["t_a"])
    stalled = m[(m["t_b"].isna() | (m["t_b"] < m["t_a"])) & (m["t_a"] + delta < v.log_end)]
    return set(stalled.index)


def t_after(v: View, scope: str, p: dict) -> set:
    """Violation if an event of activity ``late`` occurs after the first ``final`` event of the same scope object."""
    ev = v.events_of(scope)
    fin = ev[ev["activity"].isin(_acts(p["final"]))].groupby("oid")["timestamp"].min().rename("t_f")
    late = ev[ev["activity"].isin(_acts(p["late"]))][["oid", "timestamp"]].merge(fin, on="oid")
    return set(late[late["timestamp"] > late["t_f"]]["oid"])


def t_deadline(v: View, scope: str, p: dict) -> set:
    """Violation if an ``act`` event of a scope object occurs after the deadline stored as an attribute of a related ``type`` object."""
    s_rel = v.rel[v.rel["otype"] == scope][["eid", "oid"]].rename(columns={"oid": "s"})
    t_rel = v.rel[v.rel["otype"] == p["type"]][["eid", "oid"]].rename(columns={"oid": "t"})
    ev = v.ev[v.ev["activity"].isin(_acts(p["act"]))][["eid", "timestamp"]]
    m = s_rel.merge(t_rel, on="eid").merge(ev, on="eid")
    dl = pd.to_datetime(v.objattrs[p["attr"]], utc=True, errors="coerce").rename("deadline")
    m = m.merge(dl, left_on="t", right_index=True)
    return set(m[m["timestamp"] > m["deadline"]]["s"])


def t_repeat(v: View, scope: str, p: dict) -> set:
    ev = v.events_of(scope)
    c = ev[ev["activity"].isin(_acts(p["a"]))].groupby("oid")["eid"].nunique()
    return set(c[c > p["k"]].index)


TEMPLATES = {"PREC": t_prec, "SODA": t_soda, "SODO": t_sodo, "LOAD": t_load, "CLOSURE": t_closure, "STALL": t_stall, "REPEAT": t_repeat, "AFTER": t_after, "DEADLINE": t_deadline}


# ----------------------------------------------------------------------------- evaluation

def _scope_universe(ocel: Ocel, pred: Predicate) -> set:
    return set(ocel.objects.loc[ocel.objects["type"] == pred.scope, "oid"])


def score(flagged: set, oracle: set, universe: set) -> dict:
    tp, fp, fn = len(flagged & oracle), len(flagged - oracle), len(oracle - flagged)
    p = tp / (tp + fp) if tp + fp else (1.0 if not oracle else 0.0)
    r = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4), "exact": flagged == oracle}


def evaluate_predicate(ocel: Ocel, pred: Predicate, views: list[View], native: View) -> list[dict]:
    universe = _scope_universe(ocel, pred)
    oracle = {o for o in pred.evaluate(native) if o in universe}
    rows = []
    for v in views:
        ok, why = pred.expressible(v)
        row = {"dataset": ocel.name, "predicate": pred.pid, "family": pred.family, "template": pred.template, "scope": pred.scope,
               "view": v.name, "view_kind": v.kind, "view_case_type": v.case_type, "view_event_rows": len(v.ev), "view_rel_rows": len(v.rel),
               "scope_units": len(universe), "oracle_positives": len(oracle), "expressible": ok, "reason": why}
        if ok:
            flagged = {o for o in pred.evaluate(v) if o in universe}
            row.update(score(flagged, oracle, universe))
            row["outcome"] = "correct" if row["exact"] else "silent_error"
        else:
            row["outcome"] = "not_expressible"
        rows.append(row)
    return rows
