"""Load OCEL files into normalised pandas tables and compute flattening statistics.

Tables returned by ``load_ocel``:
    events     one row per event   (eid, activity, timestamp, + event attributes)
    objects    one row per object  (oid, type, + object attributes)
    relations  event-to-object     (eid, oid, qualifier, activity, timestamp, otype)
    o2o        object-to-object    (oid, oid_2, qualifier)
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import unquote
from pathlib import Path

import pandas as pd
import pm4py


@dataclass
class Ocel:
    name: str
    events: pd.DataFrame
    objects: pd.DataFrame
    relations: pd.DataFrame
    o2o: pd.DataFrame

    @property
    def object_types(self) -> list[str]:
        return sorted(self.objects["type"].dropna().unique())


def _normalise(name: str, raw) -> Ocel:
    events = raw.events.rename(columns={"ocel:eid": "eid", "ocel:activity": "activity", "ocel:timestamp": "timestamp"})
    objects = raw.objects.rename(columns={"ocel:oid": "oid", "ocel:type": "type"})
    rel = raw.relations.rename(columns={"ocel:eid": "eid", "ocel:oid": "oid", "ocel:qualifier": "qualifier",
                                        "ocel:activity": "activity", "ocel:timestamp": "timestamp", "ocel:type": "otype"})
    o2o = raw.o2o.rename(columns={"ocel:oid": "oid", "ocel:oid_2": "oid_2", "ocel:qualifier": "qualifier"}) if raw.o2o is not None else pd.DataFrame(columns=["oid", "oid_2", "qualifier"])
    events["timestamp"] = pd.to_datetime(events["timestamp"], utc=True, errors="coerce")
    rel["timestamp"] = pd.to_datetime(rel["timestamp"], utc=True, errors="coerce")
    if "qualifier" not in rel.columns:
        rel["qualifier"] = None
    return Ocel(name, events.reset_index(drop=True), objects.reset_index(drop=True), rel.reset_index(drop=True), o2o.reset_index(drop=True))


def _hash_id(value: str, salt: str = "team1-ocel-study-2026") -> str:
    import hashlib
    return "H-" + hashlib.sha256((salt + value).encode()).hexdigest()[:10]


def load_ocel_bundle(path: str | Path, name: str, pseudonymise: tuple = (), max_events: int | None = None, window_quantile: float = 0.4) -> Ocel:
    """Load an OCEL 2.x parquet bundle (extracted directory) with DuckDB; no pyarrow needed.

    Only ids, activity, time and relations are kept (event attributes are not needed for structure metrics).
    ``max_events`` keeps one contiguous time window of that many events, starting at ``window_quantile`` of the log,
    so a large real log fits in memory without resampling or altering any relation.
    """
    import duckdb
    base = Path(path)
    con = duckdb.connect()
    ev_frames, obj_frames = [], []
    for f in sorted((base / "events").glob("event_*.parquet")):
        df = con.execute(f"SELECT ocel_id AS eid, ocel_time AS timestamp FROM '{f}'").df()
        df["activity"] = unquote(f.stem[len("event_"):])
        ev_frames.append(df[["eid", "activity", "timestamp"]])
    events = pd.concat(ev_frames, ignore_index=True)
    events["timestamp"] = pd.to_datetime(events["timestamp"], utc=True, errors="coerce")
    total_events = len(events)
    if max_events and total_events > max_events:
        events = events.sort_values(["timestamp", "eid"], kind="stable").reset_index(drop=True)
        start = int(window_quantile * (total_events - max_events))
        events = events.iloc[start:start + max_events].reset_index(drop=True)
    for f in sorted((base / "objects").glob("object_*.parquet")):
        df = con.execute(f"SELECT ocel_id AS oid FROM '{f}'").df()
        df["type"] = unquote(f.stem[len("object_"):])
        obj_frames.append(df)
    objects = pd.concat(obj_frames, ignore_index=True)
    con.register("sel", events[["eid"]])
    rel = con.execute(f"SELECT r.ocel_event_id AS eid, r.ocel_object_id AS oid, r.ocel_qualifier AS qualifier FROM '{base / 'relations' / 'e2o.parquet'}' r JOIN sel ON sel.eid = r.ocel_event_id").df()
    o2o = con.execute(f"SELECT ocel_source_id AS oid, ocel_target_id AS oid_2, ocel_qualifier AS qualifier FROM '{base / 'relations' / 'o2o.parquet'}'").df()
    tmap = dict(zip(objects["oid"], objects["type"]))
    rel["otype"] = rel["oid"].map(tmap)
    rel = rel.dropna(subset=["otype"]).merge(events[["eid", "activity", "timestamp"]], on="eid", how="inner")
    if max_events and total_events > max_events:
        used = set(rel["oid"])
        objects = objects[objects["oid"].isin(used)].reset_index(drop=True)
        o2o = o2o[o2o["oid"].isin(used) & o2o["oid_2"].isin(used)].reset_index(drop=True)
    if pseudonymise:
        mask = objects["type"].isin(pseudonymise)
        objects.loc[mask, "oid"] = objects.loc[mask, "oid"].map(_hash_id)
        rel.loc[rel["otype"].isin(pseudonymise), "oid"] = rel.loc[rel["otype"].isin(pseudonymise), "oid"].map(_hash_id)
    o = Ocel(name, events.reset_index(drop=True), objects.reset_index(drop=True), rel.reset_index(drop=True), o2o)
    o.total_events_in_source = total_events
    return o


def split_roles(ocel: Ocel, types: list) -> Ocel:
    """Role-aware case notions: replace type T by 'T:QUALIFIER' for the given types (e.g. EMAILADDRESS:FROM / :TO)."""
    rel = ocel.relations.copy()
    mask = rel["otype"].isin(types)
    rel.loc[mask, "otype"] = rel.loc[mask, "otype"] + ":" + rel.loc[mask, "qualifier"].astype(str)
    objs = ocel.objects.copy()
    extra = rel[mask][["oid", "otype"]].drop_duplicates().rename(columns={"otype": "type"})
    objs = pd.concat([objs[~objs["type"].isin(types)], extra], ignore_index=True)
    return Ocel(ocel.name, ocel.events, objs, rel, ocel.o2o)


def load_ocel(path: str | Path, name: str | None = None, split_role_types: tuple = (), pseudonymise: tuple = (), max_events: int | None = None) -> Ocel:
    path = Path(path)
    if path.is_dir() and (path / "ocel-meta.json").exists():
        o = load_ocel_bundle(path, name or path.name, pseudonymise, max_events)
        return split_roles(o, list(split_role_types)) if split_role_types else o
    suffix = path.suffix.lower()
    if suffix == ".sqlite":
        raw = pm4py.read_ocel2_sqlite(str(path))
    elif suffix == ".xml":
        raw = pm4py.read_ocel2_xml(str(path))
    elif suffix in (".json", ".jsonocel"):
        try:
            raw = pm4py.read_ocel2_json(str(path))
        except Exception:
            raw = pm4py.read_ocel_json(str(path))
    else:
        raise ValueError(f"unsupported OCEL file type: {path.name}")
    o = _normalise(name or path.stem, raw)
    return split_roles(o, list(split_role_types)) if split_role_types else o


def flatten(ocel: Ocel, case_type: str) -> pd.DataFrame:
    """Case-centric flattening: one row per (event, object of ``case_type``).

    Mirrors pm4py's ``ocel_flattening``: events related to several objects of the
    case type are repeated (convergence); events with none are dropped (deficiency);
    only event-level attributes survive, never attributes or identities of other objects.
    """
    rel = ocel.relations[ocel.relations["otype"] == case_type][["eid", "oid"]].drop_duplicates()
    flat = rel.merge(ocel.events, on="eid", how="left").rename(columns={"oid": "case_id"})
    return flat.sort_values(["case_id", "timestamp", "eid"], kind="stable").reset_index(drop=True)


def flattening_stats(ocel: Ocel, case_type: str) -> dict:
    """Deficiency, convergence and divergence for one case notion."""
    n_events = len(ocel.events)
    rel_t = ocel.relations[ocel.relations["otype"] == case_type][["eid", "oid"]].drop_duplicates()
    covered = rel_t["eid"].nunique()
    per_event = rel_t.groupby("eid")["oid"].nunique()
    stats = {
        "case_type": case_type,
        "cases": int(rel_t["oid"].nunique()),
        "events": n_events,
        "flat_rows": int(len(rel_t)),
        "row_multiplier": round(len(rel_t) / n_events, 3) if n_events else None,
        "deficiency_share": round(1 - covered / n_events, 4) if n_events else None,
        "convergence_share": round(float((per_event > 1).mean()), 4) if covered else 0.0,
    }
    # Divergence: within a case, the same activity occurs >= 2 times and the repeated
    # events differ in the set of objects of at least one other type.
    other = ocel.relations[ocel.relations["otype"] != case_type][["eid", "otype", "oid"]].drop_duplicates()
    if other.empty or rel_t.empty:
        stats["divergence_share"] = 0.0
        return stats
    act = ocel.events[["eid", "activity"]]
    case_events = rel_t.merge(act, on="eid")
    reps = case_events.groupby(["oid", "activity"])["eid"].transform("count") > 1
    case_events = case_events[reps]
    if case_events.empty:
        stats["divergence_share"] = 0.0
        return stats
    total_pairs = case_events[["oid", "activity"]].drop_duplicates().shape[0]
    sig = (other.sort_values(["eid", "otype", "oid"]).groupby(["eid", "otype"])["oid"].agg(lambda s: "|".join(s)).reset_index())
    merged = case_events.merge(sig, on="eid", how="left")
    diverging = merged.groupby(["oid_x", "activity", "otype"])["oid_y"].nunique()
    diverging_pairs = diverging[diverging > 1].reset_index()[["oid_x", "activity"]].drop_duplicates().shape[0]
    stats["divergence_share"] = round(diverging_pairs / total_pairs, 4)
    return stats


def profile(ocel: Ocel) -> dict:
    """Counts, type inventories and per-case-notion flattening statistics."""
    ev_types = ocel.events["activity"].value_counts().to_dict()
    ob_types = ocel.objects["type"].value_counts().to_dict()
    rel_card = (ocel.relations.groupby(["eid"])["oid"].nunique().describe()[["mean", "50%", "max"]].round(2).to_dict())
    return {
        "name": ocel.name,
        "events": int(len(ocel.events)),
        "objects": int(len(ocel.objects)),
        "e2o_rows": int(len(ocel.relations)),
        "o2o_rows": int(len(ocel.o2o)),
        "time_span": [str(ocel.events["timestamp"].min()), str(ocel.events["timestamp"].max())],
        "event_attribute_columns": [c for c in ocel.events.columns if c not in ("eid", "activity", "timestamp")][:40],
        "activities": {k: int(v) for k, v in ev_types.items()},
        "object_types": {k: int(v) for k, v in ob_types.items()},
        "qualifiers": {k: int(v) for k, v in ocel.relations["qualifier"].fillna("<none>").value_counts().head(40).items()},
        "objects_per_event": rel_card,
        "flattening": [flattening_stats(ocel, t) for t in ocel.object_types],
    }
