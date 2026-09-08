# Audit Trail

The Educational Capstone Portal records an immutable `AuditLog` row for every state transition in the submission and review lifecycles, providing a chronological record of who acted, what changed, and the resulting status. This document describes what is audited, the actors involved, and where the current implementation falls short of full compliance auditing.

## Purpose

The audit trail exists to answer "who did what, when, and with what outcome" for the security- and integrity-sensitive parts of the capstone workflow: project creation, report compilation, submission, and faculty verification decisions. Business rule (canonical): **every state transition writes an `AuditLog` row**, giving each submission an append-only history that supports accountability and post-hoc dispute resolution.

## Scope

In scope: audit records emitted by the live submission state machine (`app/modules/reports/services/state.py`) and the supporting upload/compile flow, including the `AuditLog` schema, the action vocabulary, and the principal versus system actors that appear on each row.

Out of scope: notification delivery (handled by the event bus and notification writer), and score-correction auditing, which is not implemented (see Future Enhancements, G4).

## Responsibilities

The audit subsystem is responsible for capturing the following categories of records as immutable rows.

### Audit Events

An audit event is one `AuditLog` row written as a side effect of a state transition. The grounded action vocabulary includes:

- `PROJECT_CREATED` — emitted when a project enters `IDLE` / `NOT_SUBMITTED` at version 1.
- `COMPILATION_STARTED`, `COMPILATION_SUCCESS`, `COMPILATION_FAILED` — the LaTeX compilation lifecycle (`IDLE → PROCESSING → SUCCESS | FAILED`). Compilation failures are free retries and do not consume an attempt.
- `STUDENT_SUBMITTED` — student leader submits a successfully compiled report for review (`SUCCESS → SUBMITTED`).
- `FACULTY_STARTED_VERIFICATION` — faculty opens verification (`SUBMITTED → UNDER_VERIFICATION`).
- `FACULTY_ACCEPTED` — faculty accepts the submission (`UNDER_VERIFICATION → ACCEPTED`).
- `FACULTY_REJECTED` — faculty rejects the submission (`UNDER_VERIFICATION → NOT_SUBMITTED`, decrementing `max_tries` and incrementing `version`).

### State Changes

Audit rows are the durable trace of the dual-axis submission machine. Each transition described in the transitions table (`create_project`, `start_compilation`, `compilation_success`/`compilation_failed`, `submit_for_review`, `start_verification`, `accept_submission`, `reject_submission`) produces a row capturing the action and the resulting `status`. Note that the `REJECTED` resting state is dead code (G7): `reject_submission` sets `NOT_SUBMITTED`, never `REJECTED`, so `REJECTED` appears only as an `AuditLog.status` value and never as a live `submission_status`.

### User Actions

Principal-actor rows attribute the change to a human:

- Student actions (`STUDENT_SUBMITTED`, plus compilation triggered by the student) record the acting student via `student_reg`.
- Faculty actions (`FACULTY_STARTED_VERIFICATION`, `FACULTY_ACCEPTED`, `FACULTY_REJECTED`) record the acting faculty via `faculty_id`.

### System Actions

System-actor rows attribute the change to an automated component rather than a person. These set `system_actor` to one of:

- `CELERY_WORKER` — the Report Processing Service (Celery LaTeX compile worker) writes compilation lifecycle rows.
- `SYSTEM` — other automated transitions not attributable to a specific user.

## Workflow References

- Message-level view of the audited upload → compile → review → decision flow: [submission sequence](../diagrams/submission-sequence.md).
- Status transitions that each generate an audit row: [submission state machine](../diagrams/submission-state-machine.md).

## Business Rules

- Every state transition writes an `AuditLog` row.
- `AuditLog` fields: `project_id`, `action`, `status`, `details`, `student_reg`, `faculty_id`, `system_actor`, `created_at`.
- User-driven rows populate `student_reg` or `faculty_id`; automated rows populate `system_actor` (`CELERY_WORKER` or `SYSTEM`).
- The `status` field records the resulting submission status, including the otherwise-unreachable `REJECTED` value (G7).
- Scores are immutable once written (unique constraint + `SERIALIZABLE`); the audit trail therefore records the write but not any subsequent value correction, because none is permitted.

### Compliance Requirements

For accountability the audit trail must remain append-only and attribute every transition to either a principal (`student_reg` / `faculty_id`) or a system actor (`system_actor`). The current schema satisfies attribution and chronology (`created_at`) for the submission lifecycle. It does not yet capture field-level before/after values, which limits its usefulness for auditing data corrections such as score edits (see Future Enhancements, G4).

## Constraints

- The audit schema is denormalized to a single `AuditLog` table keyed by `project_id`; it is not a generic event store.
- Legacy compatibility constraint: `AuditLog.faculty_id` is a plain `String`, **not** a foreign key to `faculty.id`. Referential integrity for the faculty attribution is therefore not enforced at the database level, and stale or malformed faculty identifiers are possible on historical rows.
- The free-form `details` field is the only place for contextual metadata; there are no structured columns for change payloads.

## Edge Cases

- A faculty member who is also an admin (E14) is recorded under `faculty_id` for verification actions, but the audit trail carries no conflict-of-interest marker; self-approval of a related proposal is auditable only by inspecting `details`.
- Concurrent `start_verification` (E10) uses a non-locking `SELECT`, so two near-simultaneous transitions can each emit a `FACULTY_STARTED_VERIFICATION` row racing to `UNDER_VERIFICATION`.

## Security Considerations

- The audit trail is the primary integrity record for verification decisions; it must not be writable through any path other than the state machine transitions.
- Because `AuditLog.faculty_id` is an unconstrained `String`, downstream consumers must treat it as an opaque identifier and not assume it joins cleanly to the `faculty` table.
- Audit rows should be retained even when the underlying project is archived, so the chronological record survives lifecycle terminal states.

## Implementation Notes

- The live submission state machine that emits the audit rows lives in `app/modules/reports/services/state.py`.
- Compilation rows attributed to `CELERY_WORKER` originate in the Celery worker path (`app/workers/queue_worker.py`, `app/tasks/compile_task.py`, `app/modules/reports/services/compile.py`).
- The `AuditLog` model is defined under `app/shared/models/*` (`audit_log`).
- Score writes, which are not separately audited beyond the transition row, are performed by `app/services/project_service.py` (`add_project_score`, under `SERIALIZABLE`).

## Future Enhancements

- **G4 — score-correction auditing absent.** `[GAP]` There is no `is_editable` flag and no separate edited-value storage; scores overwrite in place with no before/after capture and no score-correction-specific audit fields. A `[Planned]` enhancement is to add field-level change capture (old value, new value, editor, reason) so that any future score-correction path is fully auditable. Until then, the audit trail records that a score row was written but cannot reconstruct a corrected value because correction is not supported (see E6).
