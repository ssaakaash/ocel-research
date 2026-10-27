#!/usr/bin/env python3
"""Process-discovery consequence (C5): what model does an analyst get from each flat view?

For every analysed case notion T (at least 1,000 covered events) the flat log of T is mined with the Inductive Miner
(pm4py, noise threshold 0.2) and the model is scored on the same flat log:
  fitness              token-based replay log fitness
  precision            token-based replay precision, computed only when the sum of squared case lengths is at most
                       PRECISION_BUDGET (it replays every prefix, so container notions with cases of thousands of
                       events are out of reach); otherwise null
  size                 process-tree nodes, and places, transitions (visible and silent) and arcs of the Petri net
  loop_share           share of the model's activities that sit inside a loop operator (1.0 for a "flower" model)
  activity_coverage    share of the log's activities that appear as visible transitions
Each case notion runs in a child process with a budget of TIME_BUDGET seconds; a notion that does not finish (the
Inductive Miner and token replay both slow down on cases of tens of thousands of events) is recorded with
"completed": false and no metrics.
An object-centric Petri net (one net per object type, merged) contains every activity by construction, so
activity_coverage is also the share of the object-centric model that the flat model shows. Across notions, Spearman
correlations relate fitness, precision and size to the distortion metrics in results/distortion/.

Run: realdata/.venv/bin/python -I realdata/src/discovery.py [log ...]
"""

from __future__ import annotations

import csv
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import pm4py
from pm4py.objects.process_tree.obj import Operator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from consequence import MIN_NOTION_EVENTS  # noqa: E402
from ocel_io import flatten, load_ocel  # noqa: E402
from profile_all import DATASETS, LOAD_OPTIONS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "discovery"
NOISE = 0.2
PRECISION_BUDGET = 20_000_000   # sum of squared case lengths
TIME_BUDGET = 900               # seconds per case notion
KEYS = {"case_id_key": "case_id", "activity_key": "activity", "timestamp_key": "timestamp"}


def tree_stats(tree) -> tuple[int, set, set]:
    """Number of nodes, visible labels, and labels that sit below a loop operator."""
    nodes, labels, looped = 0, set(), set()
    stack = [(tree, False)]
    while stack:
        n, in_loop = stack.pop()
        nodes += 1
        if n.label is not None:
            labels.add(n.label)
            if in_loop:
                looped.add(n.label)
        for c in n.children:
            stack.append((c, in_loop or n.operator == Operator.LOOP))
    return nodes, labels, looped


def mine(flat, out) -> None:
    """Discover and score one flat log; runs in a child process and puts the metrics on queue ``out``."""
    tree = pm4py.discover_process_tree_inductive(flat, noise_threshold=NOISE, **KEYS)
    net, im, fm = pm4py.convert_to_petri_net(tree)
    nodes, visible, looped = tree_stats(tree)
    fit = pm4py.fitness_token_based_replay(flat, net, im, fm, **KEYS)
    sq = int((flat.groupby("case_id").size().astype("int64") ** 2).sum())
    prec = pm4py.precision_token_based_replay(flat, net, im, fm, **KEYS) if sq <= PRECISION_BUDGET else None
    out.put({"sum_squared_case_length": sq, "fitness": round(float(fit["log_fitness"]), 4),
             "precision": None if prec is None else round(float(prec), 4), "tree_nodes": nodes, "places": len(net.places),
             "transitions": len(net.transitions), "silent_transitions": len(net.transitions) - len(visible), "arcs": len(net.arcs),
             "loop_share": round(len(looped) / len(visible), 4) if visible else None, "visible": sorted(visible)})


def analyse(key: str, ocel) -> dict:
    n_acts = ocel.events["activity"].nunique()
    res = {"log": key, "activities": int(n_acts), "noise_threshold": NOISE, "time_budget_s": TIME_BUDGET, "notions": []}
    ctx = mp.get_context("fork")
    for t in ocel.object_types:
        flat = flatten(ocel, t)
        if flat["eid"].nunique() < MIN_NOTION_EVENTS:
            continue
        t0 = time.time()
        flat = flat[["case_id", "activity", "timestamp"]].dropna()
        flat["case_id"] = flat["case_id"].astype(str)
        q = ctx.Queue()
        child = ctx.Process(target=mine, args=(flat, q))
        child.start()
        child.join(TIME_BUDGET)
        r = {"case_type": t, "flat_rows": int(len(flat)), "cases": int(flat["case_id"].nunique())}
        if child.is_alive() or q.empty():
            timed_out = child.is_alive()
            child.kill()
            child.join()
            r["completed"] = False
            r["stopped_by"] = "time budget" if timed_out else f"child exit code {child.exitcode}"
        else:
            m = q.get()
            r.update({"completed": True, **{k: v for k, v in m.items() if k != "visible"},
                      "activity_coverage": round(len(m["visible"]) / n_acts, 4)})
        r["seconds"] = round(time.time() - t0, 1)
        res["notions"].append(r)
        print(f"  {t[:28]:28s} " + (f"fit={r['fitness']} prec={r['precision']} loop={r['loop_share']} nodes={r['tree_nodes']} "
              f"cov={r['activity_coverage']}" if r["completed"] else f"not completed ({r['stopped_by']})") + f" ({r['seconds']} s)", flush=True)
    return res


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = set(sys.argv[1:]) or set(DATASETS)
    for key, path in DATASETS.items():
        if key not in wanted or not Path(path).exists():
            continue
        print(f"=== {key}", flush=True)
        res = analyse(key, load_ocel(path, key, **LOAD_OPTIONS.get(key, {})))
        (OUT / f"{key}.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
