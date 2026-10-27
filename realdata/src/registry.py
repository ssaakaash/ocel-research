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
LEADING = {
    "order_management": [("packages", ["items"]), ("orders", ["items"])],
    "container_logistics": [("Transport Document", ["Container"])],
    "p2p_park": [("purchase_order", ["goods receipt", "invoice receipt", "payment"])],
}


def build(key: str, ocel: Ocel) -> list[Predicate]:
    mp = make_predicate
    if key == "p2p_berti":
        k = _adaptive_k(ocel, "Supplier", "Purchase Order", "Send PO to Supplier", "Receive Goods")
        return [
            mp("P2P-1", "stage_order", "PREC", "Invoice", "payment only after a successful three-way match", first="Three-way Match - Successful", then="Make Payment"),
            mp("P2P-2", "stage_order", "PREC", "Purchase Order", "PO approved before it is sent to the supplier", first="Approve PO", then="Send PO to Supplier"),
            mp("P2P-3", "actor_conflict", "SODA", "Purchase Requisition", "requisition creator differs from approver (attribute 'user')", a="Create PR", b="Approve PR", attr_a="user", attr_b="user"),
            mp("P2P-4", "actor_conflict", "SODA", "Purchase Order", "PO creator differs from PO approver (attribute 'user')", a=["Create PO", "Create PO (Batch)"], b="Approve PO", attr_a="user", attr_b="user"),
            mp("P2P-5", "capacity", "LOAD", "Supplier", f"supplier has at most {k} POs open (sent, goods not yet received)", item="Purchase Order", open="Send PO to Supplier", close="Receive Goods", k=k),
            mp("P2P-6", "stall", "STALL", "Purchase Order", "goods received within 5 days of sending the PO", a="Send PO to Supplier", then="Receive Goods", days=5),
            mp("P2P-7", "retry_limit", "REPEAT", "Invoice", "an invoice is paid at most once", a="Make Payment", k=1),
        ]
    if key == "hiring":
        k1 = _adaptive_k(ocel, "Interviewer", "Candidate", "Schedule Panel Interview", "Conduct Panel Interview")
        k2 = _adaptive_k(ocel, "Recruiter", "Candidate", "Schedule Initial Interview", "Conduct Initial Interview")
        return [
            mp("HIR-1", "stage_order", "PREC", "Candidate", "background check completed before the offer letter is prepared", first="Complete Background Check", then="Prepare Offer Letter"),
            mp("HIR-2", "stage_order", "PREC", "Candidate", "initial interview precedes panel interview", first="Conduct Initial Interview", then="Conduct Panel Interview"),
            mp("HIR-4", "capacity", "LOAD", "Interviewer", f"interviewer has at most {k1} panel interviews scheduled-but-not-held", item="Candidate", open="Schedule Panel Interview", close="Conduct Panel Interview", k=k1),
            mp("HIR-5", "capacity", "LOAD", "Recruiter", f"recruiter has at most {k2} initial interviews scheduled-but-not-held", item="Candidate", open="Schedule Initial Interview", close="Conduct Initial Interview", k=k2),
            mp("HIR-6", "stall", "STALL", "Candidate", "an offer is answered within 30 days", a="Send Offer Letter", then=["Candidate Accept Offer", "Candidate Reject Offer"], days=30),
        ]
    if key == "o2c":
        return [
            mp("O2C-1", "stage_order", "PREC", "Order", "credit check before order approval", first="Perform Credit Check", then="Approve Order"),
            mp("O2C-2", "stage_order", "PREC", "Order", "approval before pick list", first="Approve Order", then="Generate Pick List"),
            mp("O2C-3", "stage_order", "PREC", "Order", "items packed before the order ships", first="Pack Items", then="Ship Order"),
            mp("O2C-4", "stage_order", "PREC", "Invoice", "invoice sent before payment is received", first="Send Invoice to Customer", then="Receive Payment"),
            mp("O2C-5", "stall", "STALL", "Invoice", "payment received within 30 days of the invoice being sent", a="Send Invoice to Customer", then="Receive Payment", days=30),
        ]
    if key == "hospital":
        k1 = _adaptive_k(ocel, "Nurse", "Patient", "Registration", "Assign Bed")
        k2 = _adaptive_k(ocel, "Physician", "Patient", "Pre-Admission Consultation", "Initial Evaluation")
        return [
            mp("HOS-1", "stage_order", "PREC", "Patient", "registration before initial evaluation", first="Registration", then="Initial Evaluation"),
            mp("HOS-2", "stage_order", "PREC", "Patient", "insurance verified before bed assignment", first="Insurance Verification", then="Assign Bed"),
            mp("HOS-3", "stage_order", "PREC", "Patient", "diagnostic order before the diagnostic test", first="Diagnostic Test Order", then="Perform Diagnostic Test"),
            mp("HOS-4", "capacity", "LOAD", "Nurse", f"nurse registers at most {k1} patients awaiting a bed", item="Patient", open="Registration", close="Assign Bed", k=k1),
            mp("HOS-5", "capacity", "LOAD", "Physician", f"physician has at most {k2} patients between consultation and evaluation", item="Patient", open="Pre-Admission Consultation", close="Initial Evaluation", k=k2),
            mp("HOS-6", "actor_conflict", "SODO", "Patient", "physician who consults does not order the diagnostic test (same object)", resource="Physician", a="Pre-Admission Consultation", b="Diagnostic Test Order"),
        ]
    if key == "order_management":
        k = _adaptive_k(ocel, "employees", "items", "pick item", "create package")
        return [
            mp("OM-1", "stage_order", "PREC", "items", "an item is picked only after the order is confirmed", first="confirm order", then="pick item"),
            mp("OM-2", "stage_order", "PREC", "items", "a package is created before it is sent", first="create package", then="send package"),
            mp("OM-3", "actor_conflict", "SODO", "items", "picker and packer of an item are different employees", resource="employees", a="pick item", b="create package"),
            mp("OM-4", "capacity", "LOAD", "employees", f"employee has at most {k} picked-but-unpackaged items", item="items", open="pick item", close="create package", k=k),
            mp("OM-5", "consistency", "CLOSURE", "packages", "a package is sent only after all of its items are picked", child="items", scope_act="send package", child_act="pick item"),
            mp("OM-6", "stall", "STALL", "items", "a package is delivered within 14 days of being sent", a="send package", then="package delivered", days=14),
        ]
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
    if key == "container_logistics":
        k = _adaptive_k(ocel, "Vehicle", "Container", "Load to Vehicle", "Depart")
        return [
            mp("CL-1", "consistency", "CLOSURE", "Transport Document", "vehicle departs only after all containers are loaded", child="Container", scope_act="Depart", child_act="Load to Vehicle"),
            mp("CL-2", "stage_order", "PREC", "Container", "container weighed before loading to vehicle", first="Weigh", then="Load to Vehicle"),
            mp("CL-3", "stage_order", "PREC", "Container", "empty container picked up before it is loaded", first="Pick Up Empty Container", then="Load Truck"),
            mp("CL-4", "capacity", "LOAD", "Vehicle", f"vehicle has at most {k} containers loaded-but-not-departed", item="Container", open="Load to Vehicle", close="Depart", k=k),
            mp("CL-5", "retry_limit", "REPEAT", "Transport Document", "a transport document is rescheduled at most once", a="Reschedule Container", k=1),
        ]
    return []
