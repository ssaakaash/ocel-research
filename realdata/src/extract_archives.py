#!/usr/bin/env python3
"""Extract downloaded archives into new, empty directories next to them (never into the download directory).

Rejects archives with absolute or parent-relative member paths. Run: python3 -I realdata/src/extract_archives.py
"""

from __future__ import annotations

import zipfile
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "raw"
# archive -> (target directory, members to skip)
JOBS = {
    "T3a_crop/metadata.zip": ("T3a_crop_x", ()),
    "T2a_oulad/oulad_uci_349.zip": ("T2a_oulad_x", ()),
    "T4b_enron/enron_top_100000.ocel.zip": ("T4b_enron_x", ()),
    "T4c_ethereum/ethereum_blockchain.ocel.zip": ("T4c_ethereum_x", ()),
    "T4d_aoe2/age_of_empires_ocel2_10_match_filter.zip": ("T4d_aoe2_x", ("age_of_empires_ocel2_10_match_filter.json", "age_of_empires_ocel2_10_match_filter.xml")),
}


def main() -> None:
    for archive, (target, skip) in JOBS.items():
        src, dst = RAW / archive, RAW / target
        if not src.exists():
            print(f"missing: {archive}")
            continue
        if dst.exists():
            print(f"exists, skipping: {target}")
            continue
        with zipfile.ZipFile(src) as z:
            bad = [i.filename for i in z.infolist() if i.filename.startswith("/") or ".." in i.filename.split("/")]
            if bad:
                raise SystemExit(f"{archive}: unsafe member paths {bad[:3]}")
            dst.mkdir(parents=True)
            for info in z.infolist():
                if info.filename not in skip:
                    z.extract(info, dst)
        print(f"extracted {archive} -> {target}")


if __name__ == "__main__":
    main()
