"""Predicate registry: which cross-object predicates are instantiated for each dataset.

Instantiation rule (fixed before any flattening result was computed):
  * every template whose vocabulary exists in the dataset is instantiated at most a few times,
  * LOAD thresholds k are data-adaptive: floor(median of per-resource peak concurrency) on the
    native log (changed from the 75th percentile after the first run left <5 positives through ties); no flattening result is used,
  * stall horizons are set to roughly a quarter of the log's time span.
The registry file's SHA-256 is written into every results file.
"""

from __future__ import annotations

import math

import numpy as np

from cooc import Predicate, load_peaks, make_predicate, native_view
from ocel_io import Ocel


def _adaptive_k(ocel: Ocel, resource: str, item: str, open_: str | list, close: str | list) -> int:
    peaks = load_peaks(native_view(ocel), resource, {"item": item, "open": open_, "close": close})
    return max(1, math.floor(float(np.median(list(peaks.values()))))) if peaks else 1


# leading-type flattenings with declared child closure, per dataset: (leading type, [child types])
LEADING: dict = {}  # no declared child-closure views for the real logs


def build(key: str, ocel: Ocel) -> list[Predicate]:
    mp = make_predicate





    if key == "crop":
        k = _adaptive_k(ocel, "Person", "Change", ["Comment", "RequestChanges", "Review+1", "Approve", "Verify"], ["Merge", "Abandon"])
        return [
            mp("CROP-1", "stage_order", "PREC", "Change", "a change is merged only after an approval vote", first="Approve", then="Merge"),
            mp("CROP-2a", "actor_conflict", "SODO", "Change", "nobody both uploads a patch set and approves the same change (actor as object)", resource="Person", a="Upload", b="Approve"),
            mp("CROP-2b", "actor_conflict", "SODA", "Change", "nobody both uploads a patch set and approves the same change (actor as event attribute)", a="Upload", b="Approve", attr_a="actor", attr_b="actor"),
            mp("CROP-3", "finality", "AFTER", "Change", "no review votes after a change is merged or abandoned", final=["Merge", "Abandon"], late=["Approve", "RequestChanges", "Review+1", "Verify"]),
            mp("CROP-4", "retry_limit", "REPEAT", "Change", "at most 3 request-changes rounds per change (analogue of the 3-attempt rule)", a="RequestChanges", k=3),
            mp("CROP-5", "stall", "STALL", "Change", "a change is merged or abandoned within 90 days of the first upload", a="Upload", then=["Merge", "Abandon"], days=90),
            mp("CROP-6", "capacity", "LOAD", "Person", f"a participant has at most {k} simultaneously open changes (first review activity to close)", item="Change", open=["Comment", "RequestChanges", "Review+1", "Approve", "Verify"], close=["Merge", "Abandon"], k=k),
        ]
    if key == "oulad":
        return [
            mp("OUL-1", "stage_order", "PREC", "Enrollment", "no assessment submission before the student registered", first="Register", then="Submit"),
            mp("OUL-2", "finality", "AFTER", "Enrollment", "no submission after the student unregistered", final="Unregister", late="Submit"),
            mp("OUL-3", "deadline", "DEADLINE", "Enrollment", "no submission after the assessment deadline (deadline is an Assessment object attribute)", type="Assessment", attr="deadline_ts", act="Submit"),
            mp("OUL-4", "deadline", "DEADLINE", "Student", "a student has no late submission in any enrollment (deadline is an Assessment object attribute)", type="Assessment", attr="deadline_ts", act="Submit"),
        ]

    return []
