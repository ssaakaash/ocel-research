# ADR-002: Team Formation and Locking

- Status: Accepted
- Date: 2026-06-12
- Deciders: Educational Capstone Portal Lead Architecture
- Related:
  - [Project Registration architecture](../architecture/project-registration.md)
  - [Student registration flow](../diagrams/student-registration.md)

## Context

A capstone team forms around an idea or proposal before it becomes a project.
The system must answer three questions unambiguously: who may act on behalf of a
team, who is a confirmed member of it, and when the roster becomes immutable.

The data model represents team membership with the composite primary key
`student_project (project_id, student_reg_no)` and two CHECK-constrained fields:
`role ∈ {leader, member}` and `confirmation_status ∈ {pending, confirmed}`. The
idea path mirrors this with `student_project_idea_members` carrying
`member_role` and `confirmation_status ∈ {pending → confirmed | removed}` (with
the invariant that any non-pending status implies `responded_at` is set). A
**Team Leader is not a separate identity**; it is a role value on a membership
row. The leader-only submission privilege is enforced in `routers/ideas.py`,
which returns HTTP 403 ("only the team leader may submit") for non-leaders.

The two formation channels differ: the student-idea path runs a per-member
confirmation handshake (`pending → confirmed | removed`), while the
faculty-proposal path has **no** confirmation handshake. Submission of the idea
is the point at which the team is intended to lock.

## Decision

Model team membership as **rows in `student_project` keyed by
`(project_id, student_reg_no)`**, with `role` and `confirmation_status` as
attributes rather than as separate entities. Enforce **leader-only submission**
at the router layer (HTTP 403 otherwise); the leader must be a member of the
team and the team size must not exceed `max_team_size` (≤ 10).

Apply a **member confirmation handshake on the student-idea path only**
(`pending → confirmed | removed`, with `responded_at` set on any non-pending
transition). The faculty-proposal path deliberately omits the handshake.

Adopt **lock-on-submit** semantics: when the leader submits the idea for guide
review, the team roster is frozen and the formation transition proceeds (leader
submits → team locked → guide approve/reject). Locking is enforced at the
application layer.

## Rationale

- Encoding leader as a `role` value on a membership row avoids a redundant
  `TeamLeader` entity and keeps "who leads this team" as a single attribute that
  travels with membership, eliminating a class of join/consistency bugs.
- The composite PK `(project_id, student_reg_no)` is the natural identity for a
  membership edge and supports the per-project roster directly.
- Restricting submission to the leader gives a single accountable actor for the
  irreversible lock transition, which is simpler to audit than allowing any
  member to submit.
- Running the handshake only on the student path matches the governance of each
  channel: student teams self-assemble and need consent; faculty proposals are
  authored by faculty and do not.

## Consequences

### Positive

- No separate leader entity to keep in sync; leadership is one attribute.
- Per-project roster and roles are expressed by a single table with a natural
  composite key.
- A single accountable actor (the leader) performs the lock transition,
  simplifying audit.
- Channel-specific handshake keeps each formation path as simple as its
  governance requires.

### Negative / Trade-offs

- The composite PK `(project_id, student_reg_no)` scopes uniqueness to a single
  project, so it does **not** prevent one student from being a member of
  multiple projects; the "one team per student" rule depends on application-layer
  checks (G10).
- Lock-on-submit is application-enforced, not backed by a database constraint,
  so the lock's correctness depends on every submission path honoring it.
- The handshake interacts poorly with lock-on-submit: an idea is submittable
  while members are still `pending`, and the team is not auto-unlocked when a
  member declines after locking.

## Alternatives Considered

- **Separate `TeamLeader` entity.** Model leadership as its own table/relation
  rather than a role value. Rejected: it duplicates identity already present on
  the membership row, adds a join and a synchronization invariant, and yields no
  capability the `role` attribute lacks.
- **Global student-uniqueness constraint.** Add a database-level unique
  constraint making a student a member of at most one team across all projects.
  Rejected for the current schema because membership is keyed per project; a
  global guard would require a separate enforcement mechanism and is deferred as
  a follow-up (G10) rather than retrofitted ad hoc.

## Known Gaps & Follow-ups

- **G10 — Global "one team / one idea per student" guard not located.** The
  membership PK permits multi-project membership; the single-team invariant
  relies on application-layer checks. Decide between a global constraint and an
  enforced application guard, then implement it.
- **E2 — Unconfirmed members at submit.** An idea is submittable while members
  are `pending`; there is no database gate. Define and enforce whether
  confirmation is required before lock.
- **E3 — Member declines after team lock.** The team is not auto-unlocked and a
  `removed` member remains in the roster list. Define the post-lock decline
  behavior.
- **E4 — Idea rejection restart.** Whether the team lock and member rows are
  released on idea rejection is undefined. Specify the release semantics for the
  restart path.
