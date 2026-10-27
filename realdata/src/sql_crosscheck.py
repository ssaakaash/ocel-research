#!/usr/bin/env python3
"""Independent SQL re-implementation of selected CROP predicates (stdlib sqlite3 on the OCEL 2.0 SQLite file).

Cross-checks the pandas oracle in cooc.py: the flagged-change counts must match exactly.
Run: python3 -I realdata/src/sql_crosscheck.py
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "ocel" / "crop.sqlite"

BASE = """
CREATE TEMP VIEW ev AS
  SELECT e.ocel_id AS eid, e.ocel_type AS act FROM event e;
"""

def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)  # read-only: never modify the input log
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    time_tables = [t for t in tables if t.startswith("event_") and t not in ("event_object", "event_map_type")]
    cols = {t: [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")')] for t in time_tables[:1]}
    print("event tables:", time_tables[:3], "...", "cols:", cols)
    # unified event time table
    union = " UNION ALL ".join(f'SELECT ocel_id AS eid, ocel_time AS ts FROM "{t}"' for t in time_tables)
    cur.executescript(f"""
      CREATE TEMP TABLE et AS {union};
      CREATE INDEX et_e ON et(eid);
      CREATE TEMP TABLE eo AS SELECT ocel_event_id, ocel_object_id FROM event_object;
      CREATE INDEX eo_e ON eo(ocel_event_id);
      CREATE TEMP TABLE ce AS
        SELECT eo.ocel_object_id AS change_id, e.ocel_id AS eid, e.ocel_type AS act, t.ts AS ts
        FROM eo JOIN object o ON o.ocel_id = eo.ocel_object_id AND o.ocel_type = 'Change'
        JOIN event e ON e.ocel_id = eo.ocel_event_id JOIN et t ON t.eid = e.ocel_id;
      CREATE TEMP TABLE pe AS
        SELECT eo.ocel_object_id AS person_id, e.ocel_id AS eid
        FROM eo JOIN object o ON o.ocel_id = eo.ocel_object_id AND o.ocel_type = 'Person'
        JOIN event e ON e.ocel_id = eo.ocel_event_id;
      CREATE INDEX ce_c ON ce(change_id, act, ts);
      CREATE INDEX ce_e ON ce(eid);
      CREATE INDEX pe_e ON pe(eid, person_id);
    """)
    res = {}
    # CROP-1: approval must precede merge (violation: merge with no earlier-or-equal approval)
    res["CROP-1"] = cur.execute("""
      SELECT COUNT(DISTINCT m.change_id) FROM ce m
      WHERE m.act = 'Merge' AND NOT EXISTS (
        SELECT 1 FROM ce a WHERE a.change_id = m.change_id AND a.act = 'Approve' AND a.ts <= m.ts)""").fetchone()[0]
    # CROP-2a: a person is related to both an Upload and an Approve event of the same change
    res["CROP-2a"] = cur.execute("""
      SELECT COUNT(DISTINCT u.change_id) FROM ce u JOIN pe pu ON pu.eid = u.eid
      JOIN ce a ON a.change_id = u.change_id AND a.act = 'Approve' JOIN pe pa ON pa.eid = a.eid AND pa.person_id = pu.person_id
      WHERE u.act = 'Upload'""").fetchone()[0]
    # CROP-3: any vote after the first merge/abandon
    res["CROP-3"] = cur.execute("""
      SELECT COUNT(DISTINCT l.change_id) FROM ce l JOIN (SELECT change_id, MIN(ts) AS tf FROM ce WHERE act IN ('Merge','Abandon') GROUP BY change_id) f
      ON f.change_id = l.change_id WHERE l.act IN ('Approve','RequestChanges','Review+1','Verify') AND l.ts > f.tf""").fetchone()[0]
    # CROP-4: more than 3 request-changes events
    res["CROP-4"] = cur.execute("""
      SELECT COUNT(*) FROM (SELECT change_id FROM ce WHERE act = 'RequestChanges' GROUP BY change_id HAVING COUNT(DISTINCT eid) > 3)""").fetchone()[0]
    print(json.dumps(res, indent=2))
    (ROOT / "results" / "sql_crosscheck_crop.json").write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
