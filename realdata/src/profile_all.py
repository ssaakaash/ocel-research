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
    "hiring": RAW / "T1a_berti_simulated" / "03_hiring.xml",
    "hospital": RAW / "T1a_berti_simulated" / "04_hospital.xml",
    "o2c": RAW / "T1a_berti_simulated" / "01_o2c.xml",
    "p2p_berti": RAW / "T1a_berti_simulated" / "02_p2p.xml",
    "order_management": RAW / "T1b_order_management" / "order-management.sqlite",
    "container_logistics": RAW / "T1c_container_logistics" / "ContainerLogistics.sqlite",
    "p2p_park": RAW / "T1d_p2p" / "ocel2-p2p.sqlite",
    "crop": ROOT / "ocel" / "crop.sqlite",
    "oulad": ROOT / "ocel" / "oulad.sqlite",
    "angular_commits": RAW / "T1e_angular_commits" / "angular_github_commits_ocel.jsonocel",
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
        ocel = load_ocel(path, key)
        prof = profile(ocel)
        prof["source_file"] = str(path.relative_to(ROOT))
        (OUT / f"{key}.json").write_text(json.dumps(prof, indent=2, default=str), encoding="utf-8")
        print(f"[{key}] events={prof['events']} objects={prof['objects']} e2o={prof['e2o_rows']} "
              f"types={list(prof['object_types'])} ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
