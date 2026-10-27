#!/usr/bin/env python3
"""Convert CROP (Gerrit code reviews; CC BY 4.0, Zenodo 3599150) into an OCEL 2.0 SQLite log.

Objects : Change, Person (pseudonymised), Project
Events  : Upload, Comment, RequestChanges, Review+1, Approve, Verify, Merge, Abandon, Restore, Rebase
Source  : discussion.zip (author, timestamp, comment body). CSV metadata gives the final change status.
Bots    : authors whose comments are almost all CI build messages are dropped (their load is not human review load).

Run: realdata/.venv/bin/python -I realdata/src/convert_crop.py [project ...]
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import pm4py
from pm4py.objects.ocel.obj import OCEL

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "raw" / "T3a_crop" / "discussion.zip"
META = ROOT / "raw" / "T3a_crop_x" / "metadata"
OUT = ROOT / "ocel"
SALT = "team1-ocel-study-2026"  # pseudonym salt for opaque person ids (not a secret; names are already pseudonymised in CROP)

SEP = "\n-------------------------------------"
BLOCK = re.compile(r"author:\s*(?P<author>.*)\ndate:\s*(?P<date>\S+ \S+)\n(?P<body>.*)", re.S)
BUILD = re.compile(r"Build (Started|Successful|Unstable|Failed|Aborted)|hudson|jenkins", re.I)


def pseudo(name: str) -> str:
    return "P-" + hashlib.sha256((SALT + name.strip()).encode()).hexdigest()[:10]


def classify(body: str) -> tuple[str, int | None]:
    text = body.strip()
    first = text.splitlines()[0] if text else ""
    m = re.match(r"Uploaded patch set (\d+)", first)
    if m:
        return "Upload", int(m.group(1))
    if re.match(r"Change has been successfully (merged|cherry-picked|pushed)", first):
        return "Merge", None
    if first.startswith("Abandoned"):
        return "Abandon", None
    if first.startswith("Restored"):
        return "Restore", None
    m = re.match(r"Patch Set (\d+):\s*(.*)", first)
    if m:
        ps, rest = int(m.group(1)), m.group(2)
        if re.search(r"was rebased", rest):
            return "Rebase", ps
        label = rest
        if re.search(r"Code-Review\+2|Looks good to me, approved", label):
            return "Approve", ps
        if re.search(r"Code-Review-[12]|didn't submit this|Do not submit", label):
            return "RequestChanges", ps
        if re.search(r"Code-Review\+1|Looks good to me", label):
            return "Review+1", ps
        if re.search(r"Verified\+1|^Verified\b", label):
            return "Verify", ps
        return "Comment", ps
    return "Comment", None


def parse_discussion(text: str):
    if "COMMENTS" not in text:
        return
    for raw in text.split("COMMENTS", 1)[1].split(SEP):
        raw = raw.strip("\n")
        m = BLOCK.match(raw.strip())
        if m:
            yield m.group("author").strip(), m.group("date").strip(), m.group("body")


def main() -> None:
    wanted = set(sys.argv[1:])
    status = {}
    for f in META.glob("*.csv"):
        proj = f.stem
        for r in csv.DictReader(open(f, encoding="utf-8")):
            status[(proj, r["review_number"])] = r["status"]
    z = zipfile.ZipFile(ZIP)
    raw_events = []
    author_stats = defaultdict(lambda: [0, 0])  # author -> [comments, build-like comments]
    for info in z.infolist():
        if not info.filename.endswith("_discussion.txt"):
            continue
        parts = info.filename.split("/")
        proj, review = parts[1], parts[2]
        if wanted and proj not in wanted:
            continue
        for author, date, body in parse_discussion(z.read(info).decode("utf-8", "replace")):
            author_stats[author][0] += 1
            author_stats[author][1] += bool(BUILD.search(body))
            raw_events.append((proj, review, author, date, body))
    bots = {a for a, (n, b) in author_stats.items() if n >= 20 and b / n >= 0.8}
    print(f"comments parsed: {len(raw_events):,}; authors: {len(author_stats):,}; bot-like authors dropped: {len(bots)}")

    rows = []
    for proj, review, author, date, body in raw_events:
        if author in bots:
            continue
        act, ps = classify(body)
        rows.append((proj, review, author, date, act, ps))
    df = pd.DataFrame(rows, columns=["project", "review", "author", "date", "activity", "ps"])
    df["timestamp"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values(["project", "review", "timestamp"], kind="stable").reset_index(drop=True)
    df["change"] = df["project"] + "/" + df["review"]
    df["person"] = df["author"].map(pseudo)
    df["eid"] = ["e%07d" % i for i in range(len(df))]
    print("events:", len(df), "| activities:", df["activity"].value_counts().to_dict())

    events = pd.DataFrame({"ocel:eid": df["eid"], "ocel:activity": df["activity"], "ocel:timestamp": df["timestamp"],
                           "actor": df["person"], "patch_set": df["ps"]})
    changes = sorted(df["change"].unique())
    persons = sorted(df["person"].unique())
    projects = sorted(df["project"].unique())
    obj_rows = ([(c, "Change", status.get((c.split("/")[0], c.split("/")[1]), None)) for c in changes]
                + [(p, "Person", None) for p in persons] + [(p, "Project", None) for p in projects])
    objects = pd.DataFrame(obj_rows, columns=["ocel:oid", "ocel:type", "final_status"])
    rel = []
    for col, otype, qual in (("change", "Change", "change"), ("person", "Person", "actor"), ("project", "Project", "project")):
        r = pd.DataFrame({"ocel:eid": df["eid"], "ocel:oid": df[col], "ocel:qualifier": qual, "ocel:activity": df["activity"],
                          "ocel:timestamp": df["timestamp"], "ocel:type": otype})
        rel.append(r)
    relations = pd.concat(rel, ignore_index=True)
    o2o = pd.concat([pd.DataFrame({"ocel:oid": changes, "ocel:oid_2": [c.split("/")[0] for c in changes], "ocel:qualifier": "in-project"})], ignore_index=True)
    ocel = OCEL(events=events, objects=objects, relations=relations, o2o=o2o, globals={}, parameters={})
    OUT.mkdir(exist_ok=True)
    path = OUT / "crop.sqlite"
    pm4py.write_ocel2_sqlite(ocel, str(path), objects_grouping_threshold=0) if False else pm4py.write_ocel2_sqlite(ocel, str(path))
    print("wrote", path, f"({path.stat().st_size / 1e6:.1f} MB)")
    print("changes:", len(changes), "persons:", len(persons), "projects:", len(projects))


if __name__ == "__main__":
    main()
