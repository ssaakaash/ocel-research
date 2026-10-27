#!/usr/bin/env python3
"""Convert OULAD (Kuzilek et al. 2017; CC BY 4.0) tables into an OCEL 2.0 SQLite log.

Objects : Student, Presentation (module + start term), Enrollment (student x presentation), Assessment
Events  : Register, Unregister, Submit  (VLE clickstream is not used: it carries no cross-object workflow)
Time    : OULAD stores days relative to presentation start; each presentation is anchored to a nominal start date
          (B = 1 Feb, J = 1 Oct of its year), so ordering inside an enrollment is exact and across presentations is nominal.
Run: realdata/.venv/bin/python -I realdata/src/convert_oulad.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pm4py
from pm4py.objects.ocel.obj import OCEL

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw" / "T2a_oulad_x"
OUT = ROOT / "ocel"


def start(pres: str) -> pd.Timestamp:
    year, term = int(pres[:4]), pres[4]
    return pd.Timestamp(year=year, month=2 if term == "B" else 10, day=1, tz="UTC")


def main() -> None:
    reg = pd.read_csv(SRC / "studentRegistration.csv", na_values="?")
    sa = pd.read_csv(SRC / "studentAssessment.csv", na_values="?")
    asm = pd.read_csv(SRC / "assessments.csv", na_values="?")
    asm["pres"] = asm["code_module"] + "-" + asm["code_presentation"]
    sa = sa.merge(asm, on="id_assessment", how="inner")
    sa["enr"] = sa["pres"] + "-" + sa["id_student"].astype(str)
    reg["pres"] = reg["code_module"] + "-" + reg["code_presentation"]
    reg["enr"] = reg["pres"] + "-" + reg["id_student"].astype(str)

    def ts(pres_series: pd.Series, days: pd.Series) -> pd.Series:
        base = pres_series.str.split("-").str[1].map(start)
        return base + pd.to_timedelta(days, unit="D")

    ev = []
    r = reg.dropna(subset=["date_registration"])
    ev.append(pd.DataFrame({"activity": "Register", "timestamp": ts(r["pres"], r["date_registration"]), "enr": r["enr"], "student": r["id_student"], "pres": r["pres"], "asm": None, "score": None, "is_banked": None}))
    u = reg.dropna(subset=["date_unregistration"])
    ev.append(pd.DataFrame({"activity": "Unregister", "timestamp": ts(u["pres"], u["date_unregistration"]), "enr": u["enr"], "student": u["id_student"], "pres": u["pres"], "asm": None, "score": None, "is_banked": None}))
    s = sa.dropna(subset=["date_submitted"])
    ev.append(pd.DataFrame({"activity": "Submit", "timestamp": ts(s["pres"], s["date_submitted"]), "enr": s["enr"], "student": s["id_student"], "pres": s["pres"],
                            "asm": s["id_assessment"].astype(str), "score": s["score"], "is_banked": s["is_banked"]}))
    df = pd.concat(ev, ignore_index=True).sort_values(["enr", "timestamp"], kind="stable").reset_index(drop=True)
    df["eid"] = ["e%07d" % i for i in range(len(df))]
    df["student"] = "S" + df["student"].astype(int).astype(str)
    print("events:", df["activity"].value_counts().to_dict())

    events = pd.DataFrame({"ocel:eid": df["eid"], "ocel:activity": df["activity"], "ocel:timestamp": df["timestamp"], "score": df["score"], "is_banked": df["is_banked"]})
    asm_obj = asm.assign(oid=asm["id_assessment"].astype(str))
    asm_obj["deadline_ts"] = ts(asm_obj["pres"], asm_obj["date"].fillna(0)).where(asm_obj["date"].notna())
    objects = pd.concat([
        pd.DataFrame({"ocel:oid": sorted(df["student"].unique()), "ocel:type": "Student"}),
        pd.DataFrame({"ocel:oid": sorted(df["pres"].unique()), "ocel:type": "Presentation"}),
        pd.DataFrame({"ocel:oid": sorted(df["enr"].unique()), "ocel:type": "Enrollment"}),
        pd.DataFrame({"ocel:oid": asm_obj["oid"], "ocel:type": "Assessment", "assessment_type": asm_obj["assessment_type"], "weight": asm_obj["weight"], "deadline_ts": asm_obj["deadline_ts"].astype(str)}),
    ], ignore_index=True)
    rel = []
    for col, otype, qual in (("enr", "Enrollment", "enrollment"), ("student", "Student", "student"), ("pres", "Presentation", "presentation"), ("asm", "Assessment", "assessment")):
        sub = df.dropna(subset=[col])
        rel.append(pd.DataFrame({"ocel:eid": sub["eid"], "ocel:oid": sub[col], "ocel:qualifier": qual, "ocel:activity": sub["activity"], "ocel:timestamp": sub["timestamp"], "ocel:type": otype}))
    relations = pd.concat(rel, ignore_index=True)
    enr = df.drop_duplicates("enr")
    o2o = pd.concat([pd.DataFrame({"ocel:oid": enr["enr"], "ocel:oid_2": enr["student"], "ocel:qualifier": "of-student"}),
                     pd.DataFrame({"ocel:oid": enr["enr"], "ocel:oid_2": enr["pres"], "ocel:qualifier": "in-presentation"})], ignore_index=True)
    OUT.mkdir(exist_ok=True)
    path = OUT / "oulad.sqlite"
    pm4py.write_ocel2_sqlite(OCEL(events=events, objects=objects, relations=relations, o2o=o2o, globals={}, parameters={}), str(path))
    print("wrote", path, f"({path.stat().st_size / 1e6:.1f} MB); events={len(df):,} enrollments={df['enr'].nunique():,} students={df['student'].nunique():,}")


if __name__ == "__main__":
    main()
