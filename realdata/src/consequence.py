#!/usr/bin/env python3
"""Consequence analysis: how do standard process-mining outputs change when computed on a flat log instead of the
object-centric log? Real logs only, no predicates, no injected data.

Reference ("object-centric") quantities, defined exactly from the data:
  distinct events                       every event counted once
  reference pairs                       distinct pairs (e1, e2) of consecutive events in the lifecycle of at least one object
                                        (union over all object types) = the object-centric directly-follows relation
Flat(T) quantities: one row per (event, T-object); directly-follows = consecutive rows inside a case.

Outputs per log and case notion T:
  C1 activity frequencies   Spearman rho and top-3 overlap of the activity ranking, share of activities visible at all
  C2 directly-follows       perspective coverage of reference pairs (not a distortion: other object types give other
                            lifecycles), duplication of pairs, rank agreement of edge frequencies with and without
                            duplicates, largest inflation among the 10 most frequent edges, and (when T has
                            nested children) the share of flat edge instances whose edge type never occurs inside any child
  C3 variants               distinct activity sequences, variants per case, coverage of the 10 most frequent variants,
                            and the same for nested children
  C4 entity ranking         for every other type U: Spearman rho and top-10 overlap between the true number of events per
                            U-object and the row count a denormalised flat export of T gives (plain flat cannot rank U)

Run: realdata/.venv/bin/python -I realdata/src/consequence.py [log ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocel_io import load_ocel  # noqa: E402
from profile_all import DATASETS, LOAD_OPTIONS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "consequence"
MIN_NOTION_EVENTS = 1000     # case notions covering fewer events are ignored
MIN_ENTITIES = 30            # entity types with fewer objects are not ranked


def spearman(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return round(float(spearmanr(a, b).statistic), 4)


def topk_overlap(ref: np.ndarray, other: np.ndarray, k: int) -> int:
    """Size of the intersection of the top-k index sets (ties broken by index, deterministic)."""
    k = min(k, len(ref))
    top = lambda x: set(np.lexsort((np.arange(len(x)), -x))[:k])  # noqa: E731
    return len(top(ref) & top(other))


class Prepared:
    def __init__(self, ocel):
        # canonical event order: events are coded by sorted event id, so ties in time are always broken by event id
        ev = ocel.events[["eid", "activity", "timestamp"]].dropna(subset=["timestamp"]).drop_duplicates("eid").sort_values("eid").reset_index(drop=True)
        ev["ei"] = np.arange(len(ev))
        ev["ai"], self.activities = pd.factorize(ev["activity"])
        self.n_events, self.n_acts = len(ev), len(self.activities)
        self.act_of = ev["ai"].to_numpy()                      # activity code per event code (ei == row index)
        rel = ocel.relations[["eid", "oid", "otype"]].drop_duplicates().merge(ev[["eid", "ei", "timestamp"]], on="eid")
        rel["ts"] = rel["timestamp"].astype("int64") if rel["timestamp"].dtype.kind == "M" else rel["timestamp"]
        rel["ts"] = pd.to_datetime(rel["timestamp"], utc=True).dt.tz_localize(None).to_numpy("datetime64[ns]").astype(np.int64)
        self.rel = rel[["ei", "oid", "otype", "ts"]]
        self.types = sorted(self.rel["otype"].unique())
        self._pairs: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self._seq: dict[str, pd.Series] = {}

    def rows(self, t: str) -> pd.DataFrame:
        return self.rel[self.rel["otype"] == t]

    def pairs(self, t: str) -> tuple[np.ndarray, np.ndarray]:
        """Consecutive event pairs inside every T-case (flat(T) directly-follows instances)."""
        if t not in self._pairs:
            r = self.rows(t).sort_values(["oid", "ts", "ei"], kind="stable")
            case = pd.factorize(r["oid"])[0]
            e = r["ei"].to_numpy()
            same = case[:-1] == case[1:]
            self._pairs[t] = (e[:-1][same], e[1:][same])
        return self._pairs[t]

    def sequences(self, t: str) -> pd.Series:
        if t not in self._seq:
            r = self.rows(t).sort_values(["oid", "ts", "ei"], kind="stable")
            self._seq[t] = r.assign(a=self.act_of[r["ei"].to_numpy()]).groupby("oid")["a"].agg(tuple)
        return self._seq[t]


def edge_counts(act_of: np.ndarray, e1: np.ndarray, e2: np.ndarray, n_acts: int) -> np.ndarray:
    return np.bincount(act_of[e1].astype(np.int64) * n_acts + act_of[e2], minlength=n_acts * n_acts)


def variant_summary(seqs: pd.Series) -> dict:
    vc = seqs.value_counts()
    return {"cases": int(len(seqs)), "variants": int(len(vc)), "variants_per_case": round(len(vc) / len(seqs), 4),
            "top10_variant_coverage": round(float(vc.head(10).sum() / len(seqs)), 4)}


def analyse(key: str, ocel, nested: dict[str, list[str]]) -> dict:
    P = Prepared(ocel)
    N, A = P.n_events, P.n_acts
    big = [t for t in P.types if P.rows(t)["ei"].nunique() >= MIN_NOTION_EVENTS]
    # reference quantities
    act_ref = np.bincount(P.act_of, minlength=A)
    ref_keys = np.unique(np.concatenate([P.pairs(t)[0].astype(np.int64) * N + P.pairs(t)[1] for t in P.types if len(P.pairs(t)[0])]))
    ref_e1, ref_e2 = ref_keys // N, ref_keys % N
    edge_ref = edge_counts(P.act_of, ref_e1, ref_e2, A)
    ref_types = np.flatnonzero(edge_ref)
    result = {"log": key, "events_used": int(N), "activities": int(A), "reference_pairs": int(len(ref_keys)), "reference_edge_types": int(len(ref_types)), "notions": []}
    for t in big:
        rows_t = P.rows(t)
        n_cov = rows_t["ei"].nunique()
        entry = {"case_type": t, "covered_events": int(n_cov)}
        # C1 activity ranking
        act_flat = np.bincount(P.act_of[rows_t["ei"].to_numpy()], minlength=A)
        entry["C1_activity_rank_rho"] = spearman(act_ref.astype(float), act_flat.astype(float))
        entry["C1_top3_overlap"] = topk_overlap(act_ref.astype(float), act_flat.astype(float), 3)
        entry["C1_activities_visible_share"] = round(float((act_flat[act_ref > 0] > 0).mean()), 4)
        covered_ids = rows_t["ei"].unique()
        act_cov = np.bincount(P.act_of[covered_ids], minlength=A)          # same events, each counted once
        entry["C1_dup_only_rho"] = spearman(act_cov.astype(float), act_flat.astype(float))
        entry["C1_dup_only_top3_overlap"] = topk_overlap(act_cov.astype(float), act_flat.astype(float), 3)
        # C2 directly-follows
        e1, e2 = P.pairs(t)
        keys = e1.astype(np.int64) * N + e2
        uniq = np.unique(keys)
        edge_flat = edge_counts(P.act_of, e1, e2, A)
        top_ref = ref_types[np.argsort(-edge_ref[ref_types], kind="stable")[:10]]
        ratios = edge_flat[top_ref][edge_flat[top_ref] > 0] / edge_ref[top_ref][edge_flat[top_ref] > 0]
        edge_uniq = edge_counts(P.act_of, uniq // N, uniq % N, A)               # same pairs, each counted once
        top_uniq = np.flatnonzero(edge_uniq)
        entry.update({
            "C2_pairs": int(len(keys)), "C2_perspective_coverage_of_reference": round(len(uniq) / len(ref_keys), 4),
            "C2_pair_duplication": round(len(keys) / max(1, len(uniq)), 4),
            "C2_dup_only_edge_rho": spearman(edge_uniq[top_uniq].astype(float), edge_flat[top_uniq].astype(float)),
            "C2_dup_only_top10_edge_overlap": topk_overlap(edge_uniq[top_uniq].astype(float), edge_flat[top_uniq].astype(float), 10),
            "C2_edge_freq_rho": spearman(edge_ref[ref_types].astype(float), edge_flat[ref_types].astype(float)),
            "C2_top10_edge_overlap": topk_overlap(edge_ref[ref_types].astype(float), edge_flat[ref_types].astype(float), 10),
            "C2_max_inflation_top10_edges": round(float(ratios.max()), 3) if len(ratios) else None,
        })
        kids = nested.get(t, [])
        if kids:
            child_types = np.zeros(A * A, dtype=bool)
            for u in kids:
                c1, c2 = P.pairs(u)
                child_types |= edge_counts(P.act_of, c1, c2, A) > 0
            in_child = np.zeros(N, dtype=bool)
            for u in kids:
                in_child[P.rows(u)["ei"].to_numpy()] = True
            both = in_child[e1] & in_child[e2]          # only adjacencies fully inside the children's coverage
            et = P.act_of[e1[both]].astype(np.int64) * A + P.act_of[e2[both]]
            entry["C2_spurious_edge_mass_vs_children"] = round(float((~child_types[et]).mean()), 4) if len(et) else None
            entry["C2_spurious_pairs_evaluated"] = int(both.sum())
            entry["nested_children"] = kids
        # C3 variants
        entry["C3_variants"] = variant_summary(P.sequences(t))
        if kids:
            entry["C3_children_variants"] = {u: variant_summary(P.sequences(u)) for u in kids}
        # C4 entity ranking from a denormalised flat export of T
        n_t = rows_t.groupby("ei")["oid"].nunique()
        c4 = []
        for u in P.types:
            if u == t:
                continue
            ru = P.rows(u)[["ei", "oid"]].drop_duplicates()
            if ru["oid"].nunique() < MIN_ENTITIES or ru["ei"].nunique() < MIN_NOTION_EVENTS:
                continue
            true_cnt = ru.groupby("oid").size()
            flat_cnt = ru["ei"].map(n_t).fillna(0).groupby(ru["oid"]).sum().reindex(true_cnt.index)
            a, b = true_cnt.to_numpy(float), flat_cnt.to_numpy(float)
            vis = b > 0
            c4.append({"entity_type": u, "objects": int(len(a)), "rho": spearman(a, b), "top10_overlap": topk_overlap(a, b, 10),
                       "objects_invisible_share": round(float((b == 0).mean()), 4),
                       "rho_visible_only": spearman(a[vis], b[vis]) if vis.sum() >= MIN_ENTITIES else None,
                       "top10_overlap_visible_only": topk_overlap(a[vis], b[vis], 10) if vis.sum() >= 10 else None,
                       "max_count_inflation": round(float((b[vis] / a[vis]).max()), 3) if vis.any() else None})
        entry["C4_entity_rankings"] = c4
        result["notions"].append(entry)
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = set(sys.argv[1:]) or set(DATASETS)
    for key, path in DATASETS.items():
        if key not in wanted or not Path(path).exists():
            continue
        dist = json.loads((ROOT / "results" / "distortion" / f"{key}.json").read_text())
        nested = {c["case_type"]: c.get("nested_children") or [] for c in dist["case_notions"]}
        res = analyse(key, load_ocel(path, key, **LOAD_OPTIONS.get(key, {})), nested)
        (OUT / f"{key}.json").write_text(json.dumps(res, indent=2, default=str))
        print(f"\n=== {key}: events={res['events_used']:,} reference DF pairs={res['reference_pairs']:,} edge types={res['reference_edge_types']}")
        for n in res["notions"]:
            c4 = [x["rho"] for x in n["C4_entity_rankings"] if x["rho"] is not None]
            print(f"  {n['case_type'][:26]:26s} act: visible={n['C1_activities_visible_share']} rho(all)={n['C1_activity_rank_rho']} rho(dup)={n['C1_dup_only_rho']} | DF: dup={n['C2_pair_duplication']} rho(dup)={n['C2_dup_only_edge_rho']} "
                  f"top10(dup)={n['C2_dup_only_top10_edge_overlap']} maxInfl10={n['C2_max_inflation_top10_edges']} spur={n.get('C2_spurious_edge_mass_vs_children')} | var/case={n['C3_variants']['variants_per_case']} top10cov={n['C3_variants']['top10_variant_coverage']} | entity rho min/med={min(c4) if c4 else None}/{round(float(np.median(c4)), 3) if c4 else None}")


if __name__ == "__main__":
    main()
