# State Machines

The Educational Capstone Portal coordinates several explicit state machines: the overall project lifecycle, the dual-axis submission lifecycle (compilation status crossed with submission status), the review-mark lifecycle, and a write-once scoring lifecycle. This document describes the states, transitions, and guards for each and links the diagrams that visualize them.

## Purpose

To give a single authoritative description of the lifecycle states the system tracks, the guards that gate each transition, and the points where the implemented behavior diverges from the intended design. The live submission machine is implemented against the legacy `Project` model in `app/modules/reports/services/state.py`.

## Scope

In scope: the project lifecycle, the submission lifecycle (compilation × submission status), the review-mark lifecycle, and the scoring lifecycle. Out of scope: venue-booking and approval state machines and other examination subsystems (tracked under G11), which are governed by separate modules.

## Responsibilities

The state machines own validity of transitions and enforce that no action occurs out of order. Each subsection below describes one machine.

### Project Lifecycle State Machine

The project lifecycle spans formation through finalization. A project originates from one of two registration sources (`projects.registration_source`: `faculty_proposal | student_idea | manual`):

- **Student-idea path:** `student_project_ideas.status`: `pending → approved | rejected | converted_to_project`, with the invariant `(status='converted_to_project') = (converted_project_id IS NOT NULL)`. Members confirm via `student_project_idea_members.confirmation_status`: `pending → confirmed | removed` (non-pending implies `responded_at` set). The leader submits the idea (leader-only), the team locks, and the guide approves (`→ converted_to_project`, firing `ProjectConfirmed`, decrementing guide capacity, sending notifications) or rejects (`→ rejected`, discard and restart).
- **Faculty-proposal path:** `faculty_project_proposals.status`: `open → closed | converted_to_project | cancelled`; `max_team_size > 0 AND ≤ 10`. An admin approves (`→ converted_to_project`) or rejects (`→ cancelled`). This path has no member-confirmation handshake.

Once converted, the project proceeds into the report stages (R1/R2/R3) and ultimately to a locked state. Full lifecycle visualized in [project lifecycle state machine](../diagrams/project-lifecycle-state-machine.md).

### Submission Lifecycle State Machine

The submission machine (legacy `Project`, the LIVE machine) is dual-axis:

- **`compilation_status`:** `IDLE → PROCESSING → SUCCESS | FAILED`.
- **`submission_status`:** `NOT_SUBMITTED → SUBMITTED → UNDER_VERIFICATION → ACCEPTED | REJECTED`.

Counters: `version` (monotonic), `max_tries` (default 3), `content_hash` (SHA-256). Transitions and guards (`state.py`):

| Transition | Effect | Guard |
|---|---|---|
| `create_project` | `IDLE` / `NOT_SUBMITTED`, version=1, max_tries=3 | — |
| `accept_upload` | save ZIP, new `ProjectReportVersion`, reset to `IDLE` | `submission_status ∈ {NOT_SUBMITTED, REJECTED}` AND `compilation_status ≠ PROCESSING`; `.zip` only; size ≤ `MAX_COMPRESSED_SIZE_MB`; rate-limit; `SELECT … FOR UPDATE` |
| `start_compilation` | → `PROCESSING`, set content_hash | `submission_status == NOT_SUBMITTED` |
| `compilation_success` | → `SUCCESS` | — |
| `compilation_failed` | → `FAILED` (free retry) | — |
| `submit_for_review` | → `SUBMITTED`, move tmp→persistent, lock edits, set submitted_at | `compilation_status == SUCCESS` |
| `start_verification` | → `UNDER_VERIFICATION` | `submission_status == SUBMITTED` |
| `accept_submission` | → `ACCEPTED` | `submission_status == UNDER_VERIFICATION` |
| `reject_submission` | `max_tries−−`, `version++`, → `NOT_SUBMITTED`/`IDLE` | `UNDER_VERIFICATION` AND `max_tries > 0`; raises `ValueError` if `max_tries ≤ 0` |

Compilation failures are free (no `max_tries` decrement); each faculty rejection consumes one attempt. Dual-axis machine visualized in [submission state machine](../diagrams/submission-state-machine.md); the message-level flow is in [submission sequence](../diagrams/submission-sequence.md).

### Review Lifecycle State Machine

The review-mark lifecycle governs examination marks and has **no dedicated diagram**; it is described here in prose.

- **Review mark** (`review_marks.status`): `draft → confirmed → locked`, plus `edit_approved` reached after an approved mark edit-request. Marks are unique per `(event, student, entered_by)`. Confirmed or locked marks are editable only via an approved edit-request.
- **Mark edit-request:** resolves to `edit_approved` (granting the edit) or `locked` (rejected).
- **Re-review application** (`rereview_applications.status`): `pending → approved | rejected`, decided by the HOD.

### Scoring Lifecycle

Scoring is **write-once / locked**. A score row is unique per `(report_version_id, faculty_id)` (new schema) or `(project_id, version)` (legacy). `add_project_score` writes under `SERIALIZABLE`; a second write for the same version is rejected with **HTTP 400 "Scores are locked"**. Percentages are constrained to `[0,100]` or NULL. There is no `is_editable` flag and no separate edited-value column.

## Workflow References

- [Project lifecycle state machine](../diagrams/project-lifecycle-state-machine.md)
- [Submission state machine](../diagrams/submission-state-machine.md)
- [Submission sequence](../diagrams/submission-sequence.md)
- Review lifecycle and scoring lifecycle have no dedicated diagram and are described in prose above.

## Business Rules

- Compile only when `NOT_SUBMITTED`; submit only when `SUCCESS`; accept/reject only when `UNDER_VERIFICATION`.
- Max 3 attempts per stage (`max_tries=3`); each faculty rejection consumes one (`−−`, `version++`); compile failures are free.
- Scores immutable once written (unique constraint + `SERIALIZABLE`); percentages `[0,100]`.
- Review marks unique per `(event, student, examiner)`; confirmed/locked marks editable only via an approved edit-request.
- Content-hash (SHA-256) caching reuses prior compilation.

## Constraints

- The LIVE submission machine writes the **legacy `Project`** model, not the new modular models — a deliberate migration constraint (G6).
- State vocabularies are CHECK-constrained at the database level unless noted.
- `start_verification` uses a non-locking `SELECT`, unlike `accept_upload`/`reject_submission`, which take a row lock.

## Edge Cases

- **E1** — Attempts exhausted (`max_tries == 0`): faculty cannot reject and the student cannot resubmit, deadlocking the project in `UNDER_VERIFICATION` (see G9).
- **E10** — Concurrent `start_verification`: the non-locking `SELECT` allows two transitions to race to `UNDER_VERIFICATION`.
- **E15** — Cross-model write skew during migration: `Project.max_tries` versus `ProjectReportVersion.max_tries` can diverge while both layers coexist.

## Security Considerations

- Transition guards are the integrity boundary; bypassing them (for example, writing `submission_status` directly) would corrupt the lifecycle invariants.
- Scoring immutability under `SERIALIZABLE` protects against double-write tampering.
- Every transition emits an audit row, so lifecycle changes are attributable (see [audit trail](./audit-trail.md)).

## Implementation Notes

- Submission state machine: `app/modules/reports/services/state.py`.
- Upload validation and version creation: `app/modules/reports/services/upload.py`.
- Content-hash caching: `app/modules/reports/services/cache.py`.
- Scoring write and lock: `app/services/project_service.py` (`add_project_score`).
- Review events/panels/marks, edit-requests, and re-review: `app/modules/project_coordinator/`.

## Future Enhancements

- **G5 — Stage advancement R1→R2→R3 not wired.** `[GAP]` `ensure_project_report` always defaults `review_milestone='R1'`; `state.py` never advances the milestone and `max_tries` is not reset per stage. A `[Planned]` enhancement is to drive stage progression through the submission machine.
- **G7 — `REJECTED` resting state is dead code.** `[GAP]` `reject_submission` sets `NOT_SUBMITTED`, never `REJECTED`; the upload guard accepts `REJECTED` (unreachable). `REJECTED` survives only as an `AuditLog.status` value.
- **G9 — Attempts-exhausted deadlock.** `[GAP]` At `max_tries == 0`, `reject_submission` raises and the project is stuck in `UNDER_VERIFICATION` with no automated escape; the HOD re-review application exists but is not wired to the submission machine.
