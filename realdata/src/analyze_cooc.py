#!/usr/bin/env python3
"""Aggregate COOC rows into dataset-, family- and pooled-level tables with bootstrap CIs.

Run: realdata/.venv/bin/python -I realdata/src/analyze_cooc.py [--seed N]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
SEED = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 4971
RNG = np.random.default_rng(20261027)


def per_predicate(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (dataset, predicate) with portfolio-level outcomes."""
    ev = df[df["mode"] != "excluded_low_positives"].copy()
    out = []
    for (ds, pid), g in ev.groupby(["dataset", "predicate"]):
        flat = g[g["view_kind"] == "flat"]
        dfl = g[g["view_kind"] == "dflat"]
        lead = g[g["view_kind"] == "leading"]
        dfl_ok = (dfl["outcome"] == "correct")
        nat = g[g["view_kind"] == "native"].iloc[0]
        flat_ok = (flat["outcome"] == "correct")
        lead_ok = (lead["outcome"] == "correct")
        out.append({
            "dataset": ds, "predicate": pid, "family": nat["family"], "template": nat["template"], "mode": nat["mode"],
            "oracle_positives": int(nat["oracle_positives"]), "scope_units": int(nat["scope_units"]),
            "native_correct": bool(nat["outcome"] == "correct"),
            "n_flat_views": len(flat),
            "flat_expressible": int(flat["expressible"].sum()), "flat_correct": int(flat_ok.sum()),
            "flat_silent": int((flat["outcome"] == "silent_error").sum()),
            "lead_expressible": int(lead["expressible"].sum()), "lead_correct": int(lead_ok.sum()),
            "lead_silent": int((lead["outcome"] == "silent_error").sum()),
            "dflat_expressible": int(dfl["expressible"].sum()), "dflat_correct": int(dfl_ok.sum()),
            "dflat_silent": int((dfl["outcome"] == "silent_error").sum()), "any_dflat_correct": bool(dfl_ok.any()),
            "any_flat_correct": bool(flat_ok.any()), "any_flat_or_lead_correct": bool(flat_ok.any() or lead_ok.any()),
        })
    return pd.DataFrame(out)


def dataset_table(pp: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ds, g in pp.groupby("dataset"):
        n = len(g)
        sub = df[(df["dataset"] == ds) & (df["mode"] != "excluded_low_positives")]
        view_cooc = sub[sub["view_kind"] == "flat"].groupby("view")["outcome"].apply(lambda s: (s == "correct").mean())
        dview = sub[sub["view_kind"] == "dflat"].groupby("view")["outcome"].apply(lambda s: (s == "correct").mean())
        dsil = sub[sub["view_kind"] == "dflat"]
        rows.append({
            "dataset": ds, "predicates": n,
            "native_cooc_pct": round(100 * g["native_correct"].mean(), 1),
            "best_single_flat_cooc_pct": round(100 * view_cooc.max(), 1),
            "median_single_flat_cooc_pct": round(100 * view_cooc.median(), 1),
            "flat_portfolio_cooc_pct": round(100 * g["any_flat_correct"].mean(), 1),
            "best_single_dflat_cooc_pct": round(100 * dview.max(), 1),
            "median_single_dflat_cooc_pct": round(100 * dview.median(), 1),
            "dflat_portfolio_cooc_pct": round(100 * g["any_dflat_correct"].mean(), 1),
            "dflat_silent_error_pairs": int(g["dflat_silent"].sum()),
            "dflat_answered_pairs": int(g["dflat_correct"].sum() + g["dflat_silent"].sum()),
            "flat_plus_leading_portfolio_pct": round(100 * g["any_flat_or_lead_correct"].mean(), 1),
            "never_answerable_by_any_flat_pct": round(100 * (~g["any_flat_or_lead_correct"]).mean(), 1),
            "silent_error_pairs": int(g["flat_silent"].sum() + g["lead_silent"].sum()),
            "answered_pairs": int(g["flat_correct"].sum() + g["lead_correct"].sum() + g["flat_silent"].sum() + g["lead_silent"].sum()),
        })
    return pd.DataFrame(rows)


def boot(values: np.ndarray, reps: int = 5000) -> tuple[float, float, float]:
    idx = RNG.integers(0, len(values), size=(reps, len(values)))
    means = values[idx].mean(axis=1)
    return float(values.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> None:
    df = pd.concat([pd.read_csv(f) for f in sorted((RES / "rows").glob(f"*_seed{SEED}.csv"))], ignore_index=True)
    df.to_csv(RES / f"cooc_rows_seed{SEED}.csv", index=False)
    pp = per_predicate(df)
    pp.to_csv(RES / f"cooc_per_predicate_seed{SEED}.csv", index=False)
    dt = dataset_table(pp, df)
    dt.to_csv(RES / f"cooc_by_dataset_seed{SEED}.csv", index=False)

    fam = pp.groupby("family").agg(predicates=("predicate", "count"),
                                   any_dflat_correct_pct=("any_dflat_correct", lambda s: round(100 * s.mean(), 1)),
                                   any_flat_correct_pct=("any_flat_correct", lambda s: round(100 * s.mean(), 1)),
                                   any_flat_or_lead_pct=("any_flat_or_lead_correct", lambda s: round(100 * s.mean(), 1)),
                                   silent_pairs=("flat_silent", "sum")).reset_index()
    fam.to_csv(RES / f"cooc_by_family_seed{SEED}.csv", index=False)

    pooled = {}
    for col in ("native_correct", "any_flat_correct", "any_dflat_correct", "any_flat_or_lead_correct"):
        m, lo, hi = boot(pp[col].astype(float).to_numpy())
        pooled[col] = {"share": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)]}
    # single-flat-view COOC pooled over (dataset, view) pairs
    ev = df[(df["mode"] != "excluded_low_positives") & (df["view_kind"] == "flat")]
    per_view = ev.groupby(["dataset", "view"])["outcome"].apply(lambda s: (s == "correct").mean())
    m, lo, hi = boot(per_view.to_numpy())
    pooled["single_flat_view_cooc"] = {"share": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)], "views": int(len(per_view))}
    answered = ev[ev["expressible"]]
    pooled["silent_error_rate_among_answered_flat_pairs"] = {
        "silent": int((answered["outcome"] == "silent_error").sum()), "answered": int(len(answered)),
        "rate": round(float((answered["outcome"] == "silent_error").mean()), 4) if len(answered) else None}
    dev = df[(df["mode"] != "excluded_low_positives") & (df["view_kind"] == "dflat")]
    per_dview = dev.groupby(["dataset", "view"])["outcome"].apply(lambda s: (s == "correct").mean())
    m, lo, hi = boot(per_dview.to_numpy())
    pooled["single_dflat_view_cooc"] = {"share": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)], "views": int(len(per_dview))}
    dans = dev[dev["expressible"]]
    pooled["silent_error_rate_among_answered_dflat_pairs"] = {"silent": int((dans["outcome"] == "silent_error").sum()), "answered": int(len(dans)),
                                                              "rate": round(float((dans["outcome"] == "silent_error").mean()), 4) if len(dans) else None}
    pooled["predicates_evaluated"] = int(len(pp))
    pooled["predicates_excluded_low_positives"] = int(df[df["mode"] == "excluded_low_positives"].groupby(["dataset", "predicate"]).ngroups)
    pooled["predicates_natural"] = int((pp["mode"] == "natural").sum())
    pooled["predicates_injected"] = int((pp["mode"] == "injected").sum())
    (RES / f"cooc_pooled_seed{SEED}.json").write_text(json.dumps(pooled, indent=2))

    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(dt.to_string(index=False)); print(); print(fam.to_string(index=False)); print(); print(json.dumps(pooled, indent=2))
    sil = df[(df["outcome"] == "silent_error")][["dataset", "predicate", "view", "oracle_positives", "tp", "fp", "fn", "f1"]]
    print("\nSilent-error pairs:\n", sil.to_string(index=False) if len(sil) else "none")


if __name__ == "__main__":
    main()
