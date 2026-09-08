# ADR-001: Dual-Path Project Registration

- Status: Accepted
- Date: 2026-06-12
- Deciders: Educational Capstone Portal Lead Architecture
- Related:
  - [Project Registration architecture](../architecture/project-registration.md)
  - [Student registration flow](../diagrams/student-registration.md)
  - [Faculty registration flow](../diagrams/faculty-registration.md)
  - [Project lifecycle state machine](../diagrams/project-lifecycle-state-machine.md)

## Context

A capstone project may originate from two independent intake channels. A
**Student** may author an idea (`student_project_ideas`, status
`pending → approved | rejected | converted_to_project`) and assemble a team,
after which the assigned **guide** approves or rejects it. Independently, a
**Faculty** member may publish a proposal (`faculty_project_proposals`, status
`open → closed | converted_to_project | cancelled`, `max_team_size > 0 AND <= 10`)
that an **Admin** approves or rejects. Both channels must terminate in the same
canonical artifact — a row in `projects` — so that every downstream subsystem
(report processing, review, scoring) operates against a single project identity
regardless of how the project was conceived.

The two paths differ materially in governance and lifecycle: the student path
carries a member-confirmation handshake and a guide decision; the faculty path
carries no member handshake and an admin decision. The system must preserve the
provenance of each project, must keep the "is this converted?" question
unambiguous, and must keep guide guide-capacity accounting consistent when a
project is confirmed.

## Decision

Adopt **two distinct registration workflows that converge on a single
`projects` table**, tagged by a `registration_source` enum
(`faculty_proposal | student_idea | manual`). The project also carries an
optional `project_type` (`ug | pg | integrated_pg`, nullable).

Convert-to-project is modeled as an explicit transition guarded by a
**biconditional invariant** on the originating idea:
`(student_project_ideas.status = 'converted_to_project') = (converted_project_id IS NOT NULL)`.
A converted idea is therefore one — and only one — that holds a non-null
`converted_project_id`; the two facts can never disagree. The faculty path
mirrors this with proposal status `converted_to_project`.

Conversion fires the domain event **`ProjectConfirmed`** on the in-process
event bus (`app/shared/events`). A subscriber in
`app/modules/project_registration/events.py` **decrements guide capacity** for
the `(faculty_id, academic_year, project_type)` triple
(`faculty_guide_capacity`) and enqueues notifications via
`app/shared/notifications/writer.enqueue`. Capacity accounting is therefore
**asynchronous and event-driven**, decoupled from the synchronous approval
transaction.

## Rationale

- A single `projects` table with a `registration_source` discriminator gives
  every downstream module one stable project identity while preserving
  provenance, instead of forcing each consumer to union two heterogeneous
  origin tables.
- The biconditional invariant makes "converted" a single source of truth: there
  is no window in which status and `converted_project_id` can drift, which would
  otherwise corrupt lifecycle reporting and re-conversion logic.
- Emitting `ProjectConfirmed` keeps the approval transaction small and lets
  capacity bookkeeping and notifications evolve as independent subscribers,
  matching the established event-bus pattern already used across the codebase.

## Consequences

### Positive

- One canonical project identity for reports, reviews, and scoring; downstream
  code never branches on origin.
- Provenance is queryable (`registration_source`) for analytics and auditing.
- The biconditional invariant is self-checking and prevents conversion drift.
- Event-driven capacity decrement keeps the approval path lean and extensible.

### Negative / Trade-offs

- Two parallel intake workflows must be maintained and kept behaviorally
  consistent; each governance change touches both branches.
- Asynchronous capacity decrement is **not transactional** with confirmation:
  the `ProjectConfirmed` handler swallows the capacity `ValueError` and confirms
  the project anyway, allowing over-allocation (E5).
- The faculty-proposal rejection branch is under-specified relative to the
  student path; the `cancelled` status exists in code but the surrounding
  notify/unlock semantics are not defined (see G8).

## Alternatives Considered

- **Single unified intake.** Collapse both origins into one generic intake form
  feeding `projects` directly. Rejected: the two channels carry genuinely
  different governance (member handshake + guide decision vs. admin decision)
  and `max_team_size` semantics; a unified form would either lose those
  distinctions or accumulate conditional branching worse than two clean paths.
- **Synchronous capacity check.** Decrement and validate guide capacity inline
  within the approval transaction, rejecting confirmation on overrun. Rejected
  for now to keep the approval transaction small and consistent with the
  established event-bus pattern; the trade-off is the over-allocation gap (E5),
  recorded as a follow-up.

## Known Gaps & Follow-ups

- **G8 — Faculty-proposal rejection path under-specified.** Only the approve
  branch is fully described in prose; `cancelled` exists in code but no
  notify/unlock-team step is defined. Specify and implement the rejection
  branch.
- **G10 — Global "one team / one idea per student" guard not located.**
  Membership PK `(project_id, student_reg_no)` permits multi-project membership;
  the single-team invariant currently relies on application-layer checks. A
  global constraint or enforced application guard is a follow-up.
- **G11 — Out-of-prose subsystems.** Guide capacity, guide reassignment, and
  programme/term structure that participate in registration exist in code but
  are absent from the original requirements; document and reconcile them.
- Reconsider the synchronous-vs-asynchronous capacity check in light of E5
  (over-allocation when the decrement `ValueError` is swallowed).
