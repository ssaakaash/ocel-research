#!/usr/bin/env python3
"""Bootstrap confidence intervals for the headline consequence numbers (B replicates, fixed seed).

Two resampling units, each matched to what the statistic is computed over:
  counts        narrowed case notions (under half of the activities visible), plausible case notions (coverage >= 50 %)
                and narrowed plausible ones: events are resampled with Poisson(1) weights
  correlations  activity-rank rho (against the whole process, and from duplication alone) and entity-rank rho: the
                ranked items (activities, or visible entities) are resampled with replacement, keeping each item's pair
                of counts. Event weights are not used here: for an entity with one event, a weight w makes both its true
                count and its row count proportional to w, which manufactures a correlation that is not in the data.
Per log the median and lowest rho over case notions are reported; over all 38, the case notions below rho 0.95 from
duplication alone. The unweighted replicate reproduces the published numbers; the script checks this against
results/consequence_by_notion.csv before it starts. Intervals are 2.5 and 97.5 percentiles. They describe sampling
noise within the seven logs, not the choice of logs.

Run: realdata/.venv/bin/python -I realdata/src/bootstrap.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from consequence import MIN_ENTITIES, MIN_NOTION_EVENTS, Prepared  # noqa: E402
from ocel_io import load_ocel  # noqa: E402
from profile_all import DATASETS, LOAD_OPTIONS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
B, SEED = 200, 4971
NARROW, PLAUSIBLE, DUP = 0.5, 0.5, 0.95


def rho(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return np.nan
    return float(spearmanr(a, b).statistic)


class Log:
    """Index arrays for one log; stats(w) evaluates every quantity for event weights w."""

    def __init__(self, key: str):
        P = Prepared(load_ocel(DATASETS[key], key, **LOAD_OPTIONS.get(key, {})))
        self.key, self.N, self.A, self.act = key, P.n_events, P.n_acts, P.act_of
        self.notions = []
        for t in P.types:
            rt = P.rows(t)
            if rt["ei"].nunique() < MIN_NOTION_EVENTS:
                continue
            ei = rt["ei"].to_numpy()
            n_t = np.bincount(ei, minlength=self.N)                       # T-objects per event
            ents = []
            for u in P.types:
                if u == t:
                    continue
                ru = P.rows(u)[["ei", "oid"]].drop_duplicates()
                if ru["oid"].nunique() < MIN_ENTITIES or ru["ei"].nunique() < MIN_NOTION_EVENTS:
                    continue
                ents.append((u, ru["ei"].to_numpy(), np.unique(ru["oid"].to_numpy(), return_inverse=True)[1]))
            self.notions.append({"t": t, "ei": ei, "cov": np.flatnonzero(n_t), "n_t": n_t, "ents": ents})

    def pairs(self) -> list[dict]:
        """Per notion, the unweighted (reference, flat, counted-once) activity counts and the visible entity pairs."""
        w = np.ones(self.N)
        ref = np.bincount(self.act, w, self.A)
        out = []
        for n in self.notions:
            ents = []
            for _, ei, code in n["ents"]:
                true, flat_e = np.bincount(code), np.bincount(code, n["n_t"][ei].astype(float))
                vis = flat_e > 0
                if vis.sum() >= MIN_ENTITIES:
                    ents.append((true[vis].astype(float), flat_e[vis]))
            out.append({"t": n["t"], "ref": ref, "flat": np.bincount(self.act[n["ei"]], minlength=self.A).astype(float),
                        "once": np.bincount(self.act[n["cov"]], minlength=self.A).astype(float), "ents": ents})
        return out

    def stats(self, w: np.ndarray, entities: bool = True) -> list[dict]:
        ref = np.bincount(self.act, w, self.A)
        out = []
        for n in self.notions:
            flat = np.bincount(self.act[n["ei"]], w[n["ei"]], self.A)
            once = np.bincount(self.act[n["cov"]], w[n["cov"]], self.A)
            present = ref > 0
            ent = []
            for _, ei, code in (n["ents"] if entities else []):
                true = np.bincount(code, w[ei])
                flat_e = np.bincount(code, w[ei] * n["n_t"][ei])
                vis = (true > 0) & (flat_e > 0)
                ent.append(rho(true[vis], flat_e[vis]) if vis.sum() >= MIN_ENTITIES else np.nan)
            out.append({"t": n["t"], "rho_all": rho(ref, flat), "rho_dup": rho(once, flat),
                        "visible": float((flat[present] > 0).mean()), "coverage": float(w[n["cov"]].sum() / w.sum()),
                        "entity_min": np.nanmin(ent) if np.isfinite(ent).any() else np.nan})
        return out


def counts(per_log: dict[str, list[dict]]) -> dict:
    allv = [s for v in per_log.values() for s in v]
    return {"narrowed": sum(s["visible"] < NARROW for s in allv),
            "plausible": sum(s["coverage"] >= PLAUSIBLE for s in allv),
            "plausible_narrowed": sum(s["coverage"] >= PLAUSIBLE and s["visible"] < NARROW for s in allv)}


def item_stats(pairs: list[dict], rng: np.random.Generator | None) -> list[dict]:
    """Correlations over resampled items (rng None: the original items)."""
    pick = (lambda n: np.arange(n)) if rng is None else (lambda n: rng.integers(0, n, n))
    out = []
    for p in pairs:
        i = pick(len(p["ref"]))
        ent = [rho(a[j], b[j]) for a, b in p["ents"] for j in [pick(len(a))]]
        out.append({"t": p["t"], "rho_all": rho(p["ref"][i], p["flat"][i]), "rho_dup": rho(p["once"][i], p["flat"][i]),
                    "entity_min": np.nanmin(ent) if np.isfinite(ent).any() else np.nan})
    return out


def correlations(per_log: dict[str, list[dict]]) -> dict:
    allv = [s for v in per_log.values() for s in v]
    res = {"dup_below_095": sum(s["rho_dup"] < DUP for s in allv)}
    for k, v in per_log.items():
        res[f"{k}:rho_all_median"] = float(np.nanmedian([s["rho_all"] for s in v]))
        res[f"{k}:rho_all_min"] = float(np.nanmin([s["rho_all"] for s in v]))
        res[f"{k}:rho_dup_min"] = float(np.nanmin([s["rho_dup"] for s in v]))
        e = [s["entity_min"] for s in v if np.isfinite(s["entity_min"])]
        res[f"{k}:entity_min"] = float(min(e)) if e else np.nan
    return res


def main() -> None:
    with (RES / "consequence_by_notion.csv").open(encoding="utf-8") as h:
        published = {(r["log"], r["case_type"]): r for r in csv.DictReader(h)}
    logs = [Log(k) for k in DATASETS]
    point = {L.key: L.stats(np.ones(L.N)) for L in logs}
    for k, v in point.items():                                    # the unweighted replicate must reproduce the study
        for s in v:
            p = published[(k, s["t"])]
            for mine, theirs in (("rho_all", "act_rank_rho_all"), ("rho_dup", "act_rank_rho_dup_only"), ("visible", "act_visible_share")):
                if round(s[mine], 4) != round(float(p[theirs]), 4):
                    raise SystemExit(f"{k}/{s['t']}: {mine}={s[mine]:.4f} but published {theirs}={p[theirs]}")
    print(f"point estimates reproduce consequence_by_notion.csv ({sum(map(len, point.values()))} case notions)", flush=True)
    pairs = {L.key: L.pairs() for L in logs}
    est = {**counts(point), **correlations({k: item_stats(v, None) for k, v in pairs.items()})}
    for k, v in point.items():                                    # item-level and event-level point estimates agree
        for s, q in zip(v, item_stats(pairs[k], None)):
            if not np.isclose(s["entity_min"], q["entity_min"], equal_nan=True):
                raise SystemExit(f"{k}/{s['t']}: entity rho {s['entity_min']} vs {q['entity_min']}")
    rng = np.random.default_rng(SEED)
    reps = []
    for b in range(B):
        reps.append({**counts({L.key: L.stats(rng.poisson(1.0, L.N).astype(float), entities=False) for L in logs}),
                     **correlations({k: item_stats(v, rng) for k, v in pairs.items()})})
        if (b + 1) % 50 == 0:
            print(f"{b + 1} of {B} replicates", flush=True)
    out = {"replicates": B, "seed": SEED, "method": "Poisson bootstrap over events for counts; item bootstrap (activities, entities) for rank correlations", "quantities": {}}
    for k, v in est.items():
        xs = np.array([r[k] for r in reps], dtype=float)
        xs = xs[np.isfinite(xs)]
        out["quantities"][k] = {"estimate": round(float(v), 4), "ci_low": round(float(np.percentile(xs, 2.5)), 4),
                                "ci_high": round(float(np.percentile(xs, 97.5)), 4)}
    (RES / "bootstrap.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    lines = ["| quantity | estimate | 95% interval |", "|---|---:|---|"]
    lines += [f"| {k} | {q['estimate']} | {q['ci_low']} to {q['ci_high']} |" for k, q in out["quantities"].items()]
    (RES / "bootstrap_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
