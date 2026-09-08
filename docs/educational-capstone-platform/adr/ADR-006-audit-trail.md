# ADR-006: Audit Trail

- Status: Accepted
- Date: 2026-06-12
- Deciders: Educational Capstone Portal Lead Architecture
- Related:
  - [../architecture/audit-trail.md](../architecture/audit-trail.md)
  - [../diagrams/submission-sequence.md](../diagrams/submission-sequence.md)

## Context

The portal moves projects and submissions through several state machines (formation, the dual-axis compilation × submission machine, examination marks, venue booking). Operators, faculty, and students need a reliable record of who changed what and when, and some transitions are driven not by an authenticated principal but by background processing — Celery workers performing LaTeX compilation. A canonical, low-friction record of every transition is required for traceability and dispute resolution.

The migration-in-progress means the live submission state machine still writes the legacy `Project` (`app/modules/reports/services/state.py`), so the audit record must work across both legacy and modular code paths without coupling to a single ORM layer.

## Decision

Every state transition writes an `AuditLog` row. Transitions that are not initiated by an authenticated human are attributed to a **system actor** via a fixed convention: `system_actor="SYSTEM"` for portal-internal transitions and `system_actor="CELERY_WORKER"` for background compilation work. The legacy `faculty_id` reference on audit rows is stored as a `String`, not a foreign key, so audit entries remain writable and durable even across the two divergent data models and are never blocked by referential constraints.

## Rationale

- Writing an `AuditLog` row on every transition is the canonical business rule; making it unconditional rather than opt-in guarantees coverage and avoids gaps where a particular code path forgets to log.
- The `system_actor` convention gives non-human transitions a stable, queryable identity. Background compilation runs under `CELERY_WORKER`, distinguishing automated state changes (e.g. compile success/failure) from human decisions (accept/reject, score entry).
- Storing the legacy `faculty_id` as a `String` rather than a FK decouples audit durability from the live/legacy model split (G6). Audit rows are append-only history; binding them with a foreign key would risk write failures or cascade surprises during the migration and would prevent recording actors that exist in one model layer but not the other.

## Consequences

### Positive

- Complete, uniform transition history: accept/reject, compile outcomes, and score writes all leave a trail.
- Background and human actions are distinguishable through the `system_actor` convention without a separate logging mechanism.
- Audit writes are resilient to the live/legacy model divergence because the actor reference is a plain string rather than a constrained FK.

### Negative / Trade-offs

- The `String` `faculty_id` sacrifices referential integrity: a malformed or stale identifier can be stored, and joins to faculty records are by value rather than enforced relationship.
- The `system_actor` values are a convention, not a constraint; correctness depends on every call site using `SYSTEM`/`CELERY_WORKER` consistently.
- The audit row records the transition itself but does not capture a before/after value for score corrections, because no such correction path or edited-value storage exists (G4). The trail shows that a score was written, not what an earlier value was.

## Alternatives Considered

- **Event sourcing.** Treat the audit stream as the system of record and derive state by replaying events. Rejected: the live machines mutate ORM rows directly (notably the legacy `Project`), and re-architecting around an event log would be a large change during an already-in-progress model migration. The in-process event bus exists for notifications, not as a durable source of truth.
- **External audit pipeline.** Ship transition events to a dedicated external audit/log service. Rejected for now: it adds an external dependency and delivery-reliability concerns for a record that must be transactionally consistent with the state change. An in-database `AuditLog` row written alongside the transition keeps audit and state atomic.

## Known Gaps & Follow-ups

- **G4 — No score-correction before/after capture.** Scores are write-once with no `is_editable` flag or separate edited-value column, so the audit trail cannot record the prior value of a corrected score; it records only that a score was written. A future score edit-request mechanism (see ADR-005) would need matching audit fields to capture before/after values.
