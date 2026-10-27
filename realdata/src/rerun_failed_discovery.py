#!/usr/bin/env python3
"""Re-mine the three case notions that discovery.py could not finish, with a longer budget and peak memory recorded.

Angular branches runs into the 15-minute budget. AoE2 Match fails inside pm4py's Inductive Miner
(process_tree.utils.generic.fold) with a RecursionError on cases of up to 8,895 events at about 300 MB peak memory,
so a bigger machine alone does not fix it; AoE2 Session fails before the budget too, cause not yet traced.

Same code path as discovery.py (flatten, then discovery.mine in a forked child), with a longer time budget and the
child's peak memory recorded. Prints one JSON object per case notion; paste the output into
results/discovery_large_memory.json. The flat_rows and cases fields must match results/discovery/{log}.json.

Run (from realdata/):  python -I src/rerun_failed_discovery.py [budget_seconds]     default budget: 7200
Needs raw/T4d_aoe2_x/age_of_empires_ocel2_10_match_filter.sqlite and
raw/T1e_angular_commits/angular_github_commits_ocel.jsonocel, and pm4py==2.7.23.11.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import platform
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pm4py  # noqa: E402
from discovery import mine  # noqa: E402
from ocel_io import flatten, load_ocel  # noqa: E402
from profile_all import DATASETS, LOAD_OPTIONS  # noqa: E402

FAILED = {"aoe2": ["Match", "Session"], "angular_commits": ["branches"]}
EXPECTED = {("aoe2", "Match"): (34860, 10), ("aoe2", "Session"): (34860, 20), ("angular_commits", "branches"): (2271272, 139)}


def main() -> None:
    budget = int(sys.argv[1]) if len(sys.argv) > 1 else 7200
    ctx = mp.get_context("fork")
    print(json.dumps({"machine": platform.platform(), "python": platform.python_version(), "pm4py": pm4py.__version__,
                      "memory_gb": round(__import__("os").sysconf("SC_PAGE_SIZE") * __import__("os").sysconf("SC_PHYS_PAGES") / 2**30, 1),
                      "time_budget_s": budget}), flush=True)
    for key, types in FAILED.items():
        ocel = load_ocel(DATASETS[key], key, **LOAD_OPTIONS.get(key, {}))
        n_acts = ocel.events["activity"].nunique()
        for t in types:
            flat = flatten(ocel, t)[["case_id", "activity", "timestamp"]].dropna()
            flat["case_id"] = flat["case_id"].astype(str)
            r = {"log": key, "case_type": t, "flat_rows": int(len(flat)), "cases": int(flat["case_id"].nunique())}
            r["matches_laptop_flat_log"] = (r["flat_rows"], r["cases"]) == EXPECTED[(key, t)]
            t0 = time.time()
            q = ctx.Queue()
            child = ctx.Process(target=mine, args=(flat, q))
            child.start()
            child.join(budget)
            if child.is_alive() or q.empty():
                timed_out = child.is_alive()
                child.kill()
                child.join()
                r.update({"completed": False, "stopped_by": "time budget" if timed_out else f"child exit code {child.exitcode}"})
            else:
                m = q.get()
                child.join()
                r.update({"completed": True, **{k: v for k, v in m.items() if k != "visible"},
                          "activity_coverage": round(len(m["visible"]) / n_acts, 4)})
            r["seconds"] = round(time.time() - t0, 1)
            r["peak_child_memory_gb"] = round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 2**20, 2)  # Linux: KiB
            print(json.dumps(r), flush=True)


if __name__ == "__main__":
    main()
