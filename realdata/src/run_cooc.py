#!/usr/bin/env python3
"""Run the COOC experiment (E1): oracle vs flattened representations on public OCEL logs.

Run: realdata/.venv/bin/python -I realdata/src/run_cooc.py [dataset_key ...] [--seed N]
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry  # noqa: E402
from cooc import dflat_view, evaluate_predicate, flat_view, leading_view, native_view  # noqa: E402
from inject import MIN_POSITIVES, inject  # noqa: E402
from ocel_io import load_ocel  # noqa: E402
from profile_all import DATASETS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
SEED = 4971
INJECT_SHARE = 0.05


def build_views(ocel, key):
    views = [native_view(ocel)] + [flat_view(ocel, t) for t in ocel.object_types] + [dflat_view(ocel, t) for t in ocel.object_types]
    if len(ocel.o2o):
        for lead, children in registry.LEADING.get(key, []):
            if lead in ocel.object_types:
                views.append(leading_view(ocel, lead, children))
    return views


def run_dataset(key: str, seed: int) -> list[dict]:
    ocel = load_ocel(DATASETS[key], key)
    preds = registry.build(key, ocel)
    natural_views = build_views(ocel, key)
    rows = []
    for pred in preds:
        t0 = time.time()
        universe = set(ocel.objects.loc[ocel.objects["type"] == pred.scope, "oid"])
        natural = {o for o in pred.evaluate(natural_views[0]) if o in universe}
        mode, injected, log, views = "natural", 0, ocel, natural_views
        if len(natural) < MIN_POSITIVES:
            n = max(MIN_POSITIVES, math.ceil(INJECT_SHARE * len(universe)))
            log, injected = inject(ocel, pred, n, seed + int(hashlib.sha256(pred.pid.encode()).hexdigest(), 16) % 10_000)
            views = build_views(log, key)
            mode = "injected" if injected else "no_positives"
        for r in evaluate_predicate(log, pred, views, views[0]):
            r.update({"mode": mode, "injected_units": injected, "natural_positives": len(natural), "rationale": pred.rationale})
            rows.append(r)
        # flag predicates for which neither natural nor injected positives reached the minimum
        pos = rows[-1]["oracle_positives"]
        if pos < MIN_POSITIVES:
            for r in rows[-len(views):]:
                r["mode"] = "excluded_low_positives"
        print(f"[{key}] {pred.pid:8s} {pred.template:7s} scope={pred.scope:20s} natural={len(natural):5d} mode={rows[-1]['mode']:24s} oracle_pos={pos:5d} ({time.time() - t0:.1f}s)", flush=True)
    return rows


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    seed = SEED
    if "--seed" in sys.argv:
        seed = int(sys.argv[sys.argv.index("--seed") + 1])
        args = [a for a in args if a != str(seed)]
    keys = args or ["p2p_berti", "hiring", "o2c", "hospital", "order_management", "container_logistics", "crop", "oulad"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows").mkdir(exist_ok=True)
    for key in keys:
        pd.DataFrame(run_dataset(key, seed)).to_csv(OUT / "rows" / f"{key}_seed{seed}.csv", index=False)
    reg_hash = hashlib.sha256((Path(__file__).parent / "registry.py").read_bytes()).hexdigest()
    (OUT / f"cooc_run_seed{seed}_{'_'.join(keys)}.json").write_text(json.dumps({"seed": seed, "registry_sha256": reg_hash, "datasets": keys, "min_positives": MIN_POSITIVES, "inject_share": INJECT_SHARE}, indent=2))
    print("wrote per-dataset rows to", OUT / "rows")


if __name__ == "__main__":
    main()
