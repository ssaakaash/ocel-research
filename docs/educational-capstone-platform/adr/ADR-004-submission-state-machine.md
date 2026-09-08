# ADR-004: Dual-Axis Submission State Machine

- Status: Accepted
- Date: 2026-06-12
- Deciders: Educational Capstone Portal Lead Architecture
- Related:
  - [Submission System architecture](../architecture/submission-system.md)
  - [State Machines architecture](../architecture/state-machines.md)
  - [Submission state machine](../diagrams/submission-state-machine.md)
  - [Submission stage workflow](../diagrams/submission-stage-workflow.md)

## Context

A report submission carries two orthogonal lifecycles. One tracks whether the
LaTeX source has compiled; the other tracks where the submission sits in the
review process. Conflating them into a single status would force a combinatorial
explosion of states (every compile state crossed with every review state) and
would make guards ambiguous. The live machine
(`app/modules/reports/services/state.py`) writes the legacy `Project` and
models these as two independent axes:

- `compilation_status`: `IDLE → PROCESSING → SUCCESS | FAILED`.
- `submission_status`: `NOT_SUBMITTED → SUBMITTED → UNDER_VERIFICATION → ACCEPTED | REJECTED`.

Supporting counters are `version` (monotonic), `max_tries` (default 3), and
`content_hash` (SHA-256). Transitions are guarded: upload requires
`submission_status ∈ {NOT_SUBMITTED, REJECTED}` and `compilation_status ≠ PROCESSING`;
`start_compilation` requires `NOT_SUBMITTED`; `submit_for_review` requires
`compilation_status == SUCCESS`; `start_verification` requires `SUBMITTED`;
`accept_submission` and `reject_submission` require `UNDER_VERIFICATION`. Every
transition writes an `AuditLog` row.

## Decision

Model submission as a **dual-axis state machine** with `compilation_status` and
`submission_status` as independent fields, each advanced only through explicit,
**guarded** transition methods in `state.py`. The two axes interlock at one
point: submission may proceed only when `compilation_status == SUCCESS`.

Bound faculty rejection with **`max_tries` (default 3)**. Each
`reject_submission` consumes one attempt (`max_tries--`) and increments
`version++`, returning the submission to a re-uploadable state.
**Compile retries are free**: `compilation_failed` permits another compile with
no decrement, so only review rejections — not compile failures — count against
the attempt budget.

Treat **`ACCEPTED` as the terminal accepting state with a lock**:
`accept_submission` (from `UNDER_VERIFICATION`) finalizes the submission, and
scoring is locked once written (enforced under `SERIALIZABLE`).

## Rationale

- Two independent axes keep each lifecycle small and its guards unambiguous,
  avoiding the combinatorial blow-up of a single fused status field.
- Routing every change through guarded transition methods makes illegal
  transitions impossible by construction and gives every state change a single,
  auditable entry point (`AuditLog` per transition).
- Charging only review rejections against `max_tries` reflects intent:
  compilation is a tooling concern the student should be free to fix, whereas a
  faculty rejection is a substantive judgment that should be bounded.
- A terminal, locked `ACCEPTED` state guarantees that a finalized submission and
  its scores cannot be silently mutated afterward.

## Consequences

### Positive

- Compilation and review evolve independently; guards stay simple and explicit.
- Illegal transitions are prevented by the guard methods; each transition is
  audited.
- Free compile retries with bounded review attempts match the real cost model.
- `ACCEPTED` is unambiguously terminal and locked.

### Negative / Trade-offs

- Stage advancement R1 → R2 → R3 is not wired: `ensure_project_report` always
  defaults `review_milestone='R1'`, `state.py` never advances the milestone, and
  `max_tries` is not reset per stage (G5).
- The `REJECTED` resting state is effectively dead: `reject_submission` sets
  `NOT_SUBMITTED`, never `REJECTED`, so the upload guard's acceptance of
  `REJECTED` is unreachable and `REJECTED` survives only in `AuditLog.status`
  (G7).
- When `max_tries == 0`, `reject_submission` raises and the project is stuck in
  `UNDER_VERIFICATION` with no automated escape (G9, E1).
- The live machine writes the legacy `Project` while a parallel modular model
  exists, creating drift risk during migration (G6).

## Alternatives Considered

- **Single status field.** Collapse compilation and review into one enum.
  Rejected: it requires a state for every (compile × review) combination, makes
  guards ambiguous, and couples a tooling concern (compile) to a governance
  concern (review).
- **Unbounded retries.** Allow unlimited faculty rejection/resubmission cycles.
  Rejected: review attempts represent substantive faculty effort and academic
  governance requires a finite attempt budget; `max_tries` makes the bound
  explicit. (The current bound surfaces the exhaustion deadlock G9/E1, tracked
  as a follow-up rather than a reason to remove the bound.)

## Known Gaps & Follow-ups

- **G5 — Stage advancement R1 → R2 → R3 not wired.** Milestone always defaults
  to `R1`; `state.py` never advances it and does not reset `max_tries` per stage.
  Wire stage progression into the machine.
- **G7 — `REJECTED` resting state is dead code.** `reject_submission` sets
  `NOT_SUBMITTED`, never `REJECTED`; the upload guard's `REJECTED` branch is
  unreachable. Either implement a real `REJECTED` resting state or remove the
  dead branch.
- **G9 — Attempts-exhausted deadlock.** With `max_tries == 0`,
  `reject_submission` raises and the project is stuck `UNDER_VERIFICATION`; the
  HOD re-review application exists but is not wired to the submission machine
  (E1). Provide an automated escape path.
- **G6 — Two divergent data models.** The live machine writes legacy `Project`
  while the modular model is the migration target; this risks cross-model write
  skew (E15). Complete the cutover and retire the legacy write path.
