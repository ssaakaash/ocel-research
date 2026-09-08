#!/usr/bin/env python3
"""Generate deterministic synthetic Educational Capstone Portal lifecycles and OCEL 2.0 SQLite exports."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEED = 4971
PROJECTS = 120
FACULTY = 30
STUDENTS_PER_TEAM = 3
STAGES = ("R1", "R2", "R3")


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def type_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "", value.replace(" ", "_"))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_scenario(name: str, seed: int) -> dict:
    rng = random.Random(seed)
    objects: dict[str, dict] = {}
    events: list[dict] = []
    e2o: list[dict] = []
    o2o: list[dict] = []
    truth: list[dict] = []
    event_seq = 0

    def add_object(oid: str, otype: str, **attrs) -> None:
        objects.setdefault(oid, {"object_id": oid, "object_type": otype, "attributes_json": json.dumps(attrs, sort_keys=True)})

    def link(source: str, target: str, qualifier: str) -> None:
        o2o.append({"source_object_id": source, "target_object_id": target, "qualifier": qualifier})

    def add_event(project_id: str, event_type: str, at: datetime, stage: str, status: str,
                  actor_type: str, actor_id: str, duration_hours: float, related: list[tuple[str, str]],
                  details: dict | None = None) -> str:
        nonlocal event_seq
        event_seq += 1
        eid = f"E-{name[:3].upper()}-{event_seq:06d}"
        row = {
            "event_id": eid,
            "event_type": event_type,
            "timestamp": iso(at),
            "project_id": project_id,
            "stage": stage,
            "status": status,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "duration_hours": f"{duration_hours:.2f}",
            "details_json": json.dumps(details or {}, sort_keys=True),
            "synthetic": "true",
        }
        events.append(row)
        seen = set()
        for oid, qualifier in related:
            if (oid, qualifier) not in seen:
                e2o.append({"event_id": eid, "object_id": oid, "qualifier": qualifier})
                seen.add((oid, qualifier))
        return eid

    guide_capacity = {f"F-{i:03d}": rng.randint(4, 6) for i in range(1, FACULTY + 1)}
    guide_load = defaultdict(int)
    for fid, capacity in guide_capacity.items():
        add_object(fid, "Faculty", synthetic_role="guide", capacity=capacity)

    anomaly_codes = ("G5_STAGE_STALL", "E15_COUNTER_SKEW", "G9_ATTEMPT_DEADLOCK", "E5_CAPACITY_OVERRUN", "E10_DUPLICATE_VERIFICATION", "E12_NULL_SCORE_LOCKOUT")

    for pnum in range(1, PROJECTS + 1):
        pid = f"P-{pnum:04d}"
        tid = f"T-{pnum:04d}"
        rid = f"R-{pnum:04d}"
        fid = f"F-{((pnum - 1) % FACULTY) + 1:03d}"
        students = [f"S-{pnum:04d}-{n}" for n in range(1, STUDENTS_PER_TEAM + 1)]
        anomalies: set[str] = set()
        if name == "gap_injected":
            for code in anomaly_codes:
                if rng.random() < 0.10:
                    anomalies.add(code)
            if not anomalies and pnum % 4 == 0:
                anomalies.add(anomaly_codes[pnum % len(anomaly_codes)])

        add_object(pid, "Project", registration_source="student_idea" if pnum % 4 else "faculty_proposal", synthetic=True)
        add_object(tid, "Team", size=STUDENTS_PER_TEAM)
        add_object(rid, "Report", milestone_model="R1-R2-R3" if name != "implemented_baseline" else "R1-only")
        for sid in students:
            add_object(sid, "Student", pseudonymous=True)
            link(sid, tid, "member-of")
        link(tid, pid, "executes")
        link(fid, pid, "guides")
        link(pid, rid, "has-report")
        guide_load[fid] += 1

        start = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc) + timedelta(hours=9 * pnum)
        rel = [(pid, "affected"), (tid, "team"), (fid, "guide")] + [(sid, "member") for sid in students]
        add_event(pid, "PROJECT_CREATED", start, "", "ACTIVE", "student", students[0], 0, rel,
                  {"guide_load": guide_load[fid], "guide_capacity": guide_capacity[fid], "capacity_overrun": "E5_CAPACITY_OVERRUN" in anomalies})

        stages = ("R1",) if name == "implemented_baseline" else STAGES
        remaining = 3
        final_status = "ACTIVE"
        for stage_index, stage in enumerate(stages, 1):
            if stage_index > 1 and "G5_STAGE_STALL" in anomalies:
                break
            version = 1
            accepted = False
            while not accepted:
                vid = f"RV-{pnum:04d}-{stage}-V{version}"
                add_object(vid, "ReportVersion", stage=stage, version=version, max_tries=remaining)
                link(rid, vid, "has-version")
                # Reserve enough wall-clock space for compile, submission, review,
                # rejection, and resubmission so each synthetic trace is monotonic.
                t = start + timedelta(days=21 * (stage_index - 1) + 5 * (version - 1), hours=6)
                compile_hours = max(0.1, rng.lognormvariate(-0.2, 0.45))
                add_event(pid, "COMPILATION_STARTED", t, stage, "PROCESSING", "system", "CELERY_WORKER", 0,
                          [(pid, "affected"), (vid, "compiled")])
                fail = rng.random() < 0.12
                if fail:
                    add_event(pid, "COMPILATION_FAILED", t + timedelta(hours=compile_hours), stage, "FAILED", "system", "CELERY_WORKER", compile_hours,
                              [(pid, "affected"), (vid, "compiled")], {"attempt_consumed": False})
                    t += timedelta(hours=compile_hours + 1)
                    add_event(pid, "COMPILATION_STARTED", t, stage, "PROCESSING", "system", "CELERY_WORKER", 0,
                              [(pid, "affected"), (vid, "compiled")])
                    compile_hours = max(0.1, rng.lognormvariate(-0.25, 0.4))
                add_event(pid, "COMPILATION_SUCCESS", t + timedelta(hours=compile_hours), stage, "SUCCESS", "system", "CELERY_WORKER", compile_hours,
                          [(pid, "affected"), (vid, "compiled")], {"cache_hit": rng.random() < 0.24})
                submit_t = t + timedelta(hours=compile_hours + rng.uniform(2, 10))
                add_event(pid, "STUDENT_SUBMITTED", submit_t, stage, "SUBMITTED", "student", students[0], 0,
                          [(pid, "affected"), (tid, "submitted-by"), (vid, "submitted")] + [(sid, "team-member") for sid in students])
                verify_t = submit_t + timedelta(hours=rng.uniform(8, 72))
                details = {"legacy_remaining": remaining, "modular_remaining": remaining}
                if "E15_COUNTER_SKEW" in anomalies:
                    details["modular_remaining"] = max(0, remaining - 1)
                add_event(pid, "FACULTY_STARTED_VERIFICATION", verify_t, stage, "UNDER_VERIFICATION", "faculty", fid, 0,
                          [(pid, "affected"), (vid, "verified"), (fid, "actor")], details)
                if "E10_DUPLICATE_VERIFICATION" in anomalies and stage == "R1" and version == 1:
                    add_event(pid, "FACULTY_STARTED_VERIFICATION", verify_t + timedelta(minutes=2), stage, "UNDER_VERIFICATION", "faculty", fid, 0,
                              [(pid, "affected"), (vid, "verified"), (fid, "actor")], details)

                force_deadlock = "G9_ATTEMPT_DEADLOCK" in anomalies and stage == "R1"
                rejected = (rng.random() < 0.18 and remaining > 1) or force_deadlock
                decision_t = verify_t + timedelta(hours=rng.uniform(4, 36))
                if rejected:
                    remaining = 0 if force_deadlock else remaining - 1
                    add_event(pid, "FACULTY_REJECTED", decision_t, stage, "UNDER_VERIFICATION" if force_deadlock else "NOT_SUBMITTED", "faculty", fid,
                              (decision_t - submit_t).total_seconds() / 3600,
                              [(pid, "affected"), (vid, "decision-for"), (fid, "actor")],
                              {"remaining_attempts": remaining, "deadlock": force_deadlock})
                    if force_deadlock:
                        final_status = "UNDER_VERIFICATION"
                        break
                    version += 1
                    continue

                score_id = f"SC-{pnum:04d}-{stage}"
                score_value = None if "E12_NULL_SCORE_LOCKOUT" in anomalies and stage == "R1" else round(rng.uniform(65, 96), 1)
                add_object(score_id, "Score", value=score_value, immutable=True, stage=stage)
                link(vid, score_id, "has-score")
                link(fid, score_id, "assigns")
                add_event(pid, "FACULTY_ACCEPTED", decision_t, stage, "ACCEPTED", "faculty", fid,
                          (decision_t - submit_t).total_seconds() / 3600,
                          [(pid, "affected"), (vid, "decision-for"), (fid, "actor"), (score_id, "locks-score"), (tid, "team")],
                          {"remaining_attempts": remaining, "score_is_null": score_value is None})
                accepted = True
                final_status = "ACCEPTED"

            if final_status == "UNDER_VERIFICATION":
                break

        for code in anomaly_codes:
            truth.append({"project_id": pid, "anomaly_type": code, "is_injected": "1" if code in anomalies else "0"})

    return {"objects": list(objects.values()), "events": events, "e2o": e2o, "o2o": o2o, "truth": truth}


def export_sqlite(path: Path, data: dict) -> None:
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE event (ocel_id TEXT PRIMARY KEY, ocel_type TEXT NOT NULL);
        CREATE TABLE object (ocel_id TEXT PRIMARY KEY, ocel_type TEXT NOT NULL);
        CREATE TABLE event_object (ocel_event_id TEXT, ocel_object_id TEXT, ocel_qualifier TEXT);
        CREATE TABLE object_object (ocel_source_id TEXT, ocel_target_id TEXT, ocel_qualifier TEXT);
        CREATE TABLE event_map_type (ocel_type TEXT, ocel_type_map TEXT);
        CREATE TABLE object_map_type (ocel_type TEXT, ocel_type_map TEXT);
    """)
    event_types = sorted({row["event_type"] for row in data["events"]})
    object_types = sorted({row["object_type"] for row in data["objects"]})
    cur.executemany("INSERT INTO event VALUES (?,?)", [(r["event_id"], r["event_type"]) for r in data["events"]])
    cur.executemany("INSERT INTO object VALUES (?,?)", [(r["object_id"], r["object_type"]) for r in data["objects"]])
    cur.executemany("INSERT INTO event_object VALUES (?,?,?)", [(r["event_id"], r["object_id"], r["qualifier"]) for r in data["e2o"]])
    cur.executemany("INSERT INTO object_object VALUES (?,?,?)", [(r["source_object_id"], r["target_object_id"], r["qualifier"]) for r in data["o2o"]])
    for et in event_types:
        key = type_key(et)
        cur.execute("INSERT INTO event_map_type VALUES (?,?)", (et, key))
        cur.execute(f'CREATE TABLE "event_{key}" (ocel_id TEXT, ocel_time TIMESTAMP, stage TEXT, status TEXT, actor_type TEXT, actor_id TEXT, duration_hours REAL, details_json TEXT, synthetic BOOLEAN)')
        rows = [r for r in data["events"] if r["event_type"] == et]
        cur.executemany(f'INSERT INTO "event_{key}" VALUES (?,?,?,?,?,?,?,?,?)', [(r["event_id"], r["timestamp"], r["stage"], r["status"], r["actor_type"], r["actor_id"], float(r["duration_hours"]), r["details_json"], 1) for r in rows])
    for ot in object_types:
        key = type_key(ot)
        cur.execute("INSERT INTO object_map_type VALUES (?,?)", (ot, key))
        cur.execute(f'CREATE TABLE "object_{key}" (ocel_id TEXT, ocel_time TIMESTAMP, ocel_changed_field TEXT, attributes_json TEXT)')
        rows = [r for r in data["objects"] if r["object_type"] == ot]
        cur.executemany(f'INSERT INTO "object_{key}" VALUES (?,?,?,?)', [(r["object_id"], "1970-01-01T00:00:00Z", None, r["attributes_json"]) for r in rows])
    con.commit()
    con.close()


def validate(data: dict, sqlite_path: Path) -> dict:
    event_ids = {r["event_id"] for r in data["events"]}
    object_ids = {r["object_id"] for r in data["objects"]}
    dangling_e2o = sum(r["event_id"] not in event_ids or r["object_id"] not in object_ids for r in data["e2o"])
    dangling_o2o = sum(r["source_object_id"] not in object_ids or r["target_object_id"] not in object_ids for r in data["o2o"])
    ordered = True
    by_project = defaultdict(list)
    for row in data["events"]:
        by_project[row["project_id"]].append(row["timestamp"])
    for stamps in by_project.values():
        ordered = ordered and stamps == sorted(stamps)
    con = sqlite3.connect(sqlite_path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = {"event", "object", "event_object", "object_object", "event_map_type", "object_map_type"}
    con.close()
    digest = hashlib.sha256(sqlite_path.read_bytes()).hexdigest()
    return {"dangling_e2o": dangling_e2o, "dangling_o2o": dangling_o2o, "timestamps_monotonic_per_project": ordered, "required_tables_present": required.issubset(tables), "sha256": digest}


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    manifest = {"synthetic": True, "seed": SEED, "projects": PROJECTS, "faculty": FACULTY, "students_per_team": STUDENTS_PER_TEAM, "scenarios": {}}
    for offset, name in enumerate(("clean_target", "implemented_baseline", "gap_injected")):
        out = DATA / name
        out.mkdir(parents=True, exist_ok=True)
        data = build_scenario(name, SEED + offset)
        write_csv(out / "objects.csv", data["objects"], ["object_id", "object_type", "attributes_json"])
        write_csv(out / "events.csv", data["events"], ["event_id", "event_type", "timestamp", "project_id", "stage", "status", "actor_type", "actor_id", "duration_hours", "details_json", "synthetic"])
        write_csv(out / "e2o.csv", data["e2o"], ["event_id", "object_id", "qualifier"])
        write_csv(out / "o2o.csv", data["o2o"], ["source_object_id", "target_object_id", "qualifier"])
        write_csv(out / "anomaly_ground_truth.csv", data["truth"], ["project_id", "anomaly_type", "is_injected"])
        sqlite_path = out / f"capstone_{name}.ocel.sqlite"
        export_sqlite(sqlite_path, data)
        manifest["scenarios"][name] = {
            "events": len(data["events"]), "objects": len(data["objects"]), "e2o": len(data["e2o"]), "o2o": len(data["o2o"]),
            "validation": validate(data, sqlite_path)
        }
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
