#!/usr/bin/env python3
"""Profile every downloaded OCEL file: inventories and flattening distortion statistics.

Run: realdata/.venv/bin/python -I realdata/src/profile_all.py [dataset_key ...]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ocel_io import load_ocel, profile  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "results" / "profiles"

DATASETS = {
    "crop": ROOT / "ocel" / "crop.sqlite",
    "oulad": ROOT / "ocel" / "oulad.sqlite",
    "angular_commits": RAW / "T1e_angular_commits" / "angular_github_commits_ocel.jsonocel",
    "bundestag": RAW / "T4a_bundestag" / "Period20_procedure_steps_all_additional_event_types_filtered.json",
    "enron": RAW / "T4b_enron_x",
    "ethereum": RAW / "T4c_ethereum_x",
    "aoe2": RAW / "T4d_aoe2_x" / "age_of_empires_ocel2_10_match_filter.sqlite",
}

# per-log loader options: pseudonymise personal identifiers; role-aware case notions
LOAD_OPTIONS = {
    "enron": {"pseudonymise": ("EMAILADDRESS",), "split_role_types": ("EMAILADDRESS",)},
    "ethereum": {"max_events": 300_000},  # contiguous time window; the full log has 3.2 M events and does not fit in 8 GB RAM
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = set(sys.argv[1:]) or set(DATASETS)
    for key, path in DATASETS.items():
        if key not in wanted:
            continue
        if not path.exists():
            print(f"[{key}] missing: {path.relative_to(ROOT)}")
            continue
        t0 = time.time()
        ocel = load_ocel(path, key, **LOAD_OPTIONS.get(key, {}))
        prof = profile(ocel)
        prof["source_file"] = str(path.relative_to(ROOT))
        (OUT / f"{key}.json").write_text(json.dumps(prof, indent=2, default=str), encoding="utf-8")
        print(f"[{key}] events={prof['events']} objects={prof['objects']} e2o={prof['e2o_rows']} "
              f"types={list(prof['object_types'])} ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
