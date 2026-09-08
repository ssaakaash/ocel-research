# Faculty Review

The faculty review subsystem governs how a guide opens, examines, and decides a submitted report version. It implements the verification half of the submission state machine: moving a submission from `SUBMITTED` through `UNDER_VERIFICATION` to a terminal `ACCEPTED`, or back for another attempt on rejection.

## Purpose

Define the rules and transitions by which faculty verify student submissions, accept or reject them, consume bounded review attempts, and (in the target design) advance a project through review stages R1, R2, and R3.

## Scope

Covers `start_verification`, `accept_submission`, and `reject_submission` on the live submission machine (`app/modules/reports/services/state.py`), the per-stage attempt budget, and the intended stage progression. Score recording is covered separately in [scoring-system.md](scoring-system.md); upload and compilation are covered in [report-processing.md](report-processing.md).

### Review Process

A guide begins review with `start_verification`, which requires the submission to be `SUBMITTED` and transitions it to `UNDER_VERIFICATION`. The decision actions (`accept_submission`, `reject_submission`) are only valid while the submission is `UNDER_VERIFICATION`.

### Approval Rules

`accept_submission` requires `submission_status == UNDER_VERIFICATION` and transitions the submission to `ACCEPTED`. Acceptance is terminal for the version and does not consume an attempt.

### Rejection Rules

`reject_submission` requires `submission_status == UNDER_VERIFICATION` and `max_tries > 0`. It decrements `max_tries`, increments `version`, and returns the submission to `NOT_SUBMITTED` / `IDLE` so the student may resubmit. If `max_tries <= 0`, it raises `ValueError`. Note that the rejection path sets `NOT_SUBMITTED`, not the `REJECTED` resting state, so `REJECTED` is effectively dead in the live machine `[GAP]` (G7); it survives only in `AuditLog.status`.

### Stage Progression

The intended model is three stages — R1, R2, R3 — each with its own three-attempt budget. In the current code, stage advancement is not wired `[GAP]` (G5): `ensure_project_report` always defaults `review_milestone='R1'`, `state.py` never advances the milestone, and `max_tries` is not reset per stage. Stage progression past R1 is therefore `[Future]`.

### Submission Limits

Each stage allows a maximum of three attempts (`max_tries=3`). Every faculty rejection consumes one attempt (`max_tries--`, `version++`). Compilation failures are free and do not count against this budget (see [report-processing.md](report-processing.md)).

## Responsibilities

- Open verification on a submitted report version (`start_verification`).
- Accept a verified submission, reaching the terminal `ACCEPTED` state.
- Reject a verified submission, consuming an attempt and reopening it for resubmission.
- Enforce the three-attempts-per-stage budget and refuse rejection once exhausted.
- Record an `AuditLog` row for every transition.

## Workflow References

- [../diagrams/faculty-review-workflow.md](../diagrams/faculty-review-workflow.md) — review, Turnitin upload, manual scoring, OCR/Turnitin [Planned], decision.
- [../diagrams/submission-stage-workflow.md](../diagrams/submission-stage-workflow.md) — R1/R2/R3 stages, attempts, terminal failure.
- Related docs: [submission-state-machine diagram](../diagrams/submission-state-machine.md), [scoring-system.md](scoring-system.md), [report-processing.md](report-processing.md).

## Business Rules

- `start_verification` requires `submission_status == SUBMITTED`.
- `accept_submission` and `reject_submission` require `submission_status == UNDER_VERIFICATION`.
- A rejection consumes an attempt: `max_tries--` and `version++`.
- `reject_submission` raises `ValueError` when `max_tries <= 0`.
- Each stage permits a maximum of 3 attempts.
- Compile failures are free retries; only faculty rejections decrement `max_tries`.
- Every transition writes an `AuditLog` row.

## Constraints

- The live verification flow operates on the legacy `Project` model via `state.py`, while the modular `project_report_versions` schema is the migration target; the two model layers coexist.
- `start_verification` uses a non-locking SELECT, so concurrent calls can race (E10).
- Acceptance and rejection are the only valid decisions, and only from `UNDER_VERIFICATION`.

## Edge Cases

- **E1** — Attempts exhausted (`max_tries == 0`): faculty cannot reject and the student cannot resubmit, producing a deadlock (see G9).
- **E6** — Score immutability versus the requirement that faculty may edit values: a locked score (HTTP 400) conflicts with editing extracted values; there is no edit-request path for scores. See [scoring-system.md](scoring-system.md).
- **E10** — Concurrent `start_verification`: a non-locking SELECT allows a race to `UNDER_VERIFICATION`.
- **E13** — Guide reassignment mid-submission: the effect on in-flight verification and locked scores is undefined.

## Security Considerations

Verification actions are restricted to the guide role on the project (see [security-model.md](security-model.md)). Each transition is recorded in the audit trail, providing accountability for accept and reject decisions. There is no conflict-of-interest guard preventing a faculty member who is also an admin from acting on their own work (E14).

## Implementation Notes

- `app/modules/reports/services/state.py` — `start_verification`, `accept_submission`, `reject_submission` and their guards; defaults `review_milestone='R1'` via `ensure_project_report`.
- `app/routers/faculty.py` — faculty-facing review endpoints.
- `app/services/project_service.py` — score recording at decision time (`add_project_score`).
- `app/modules/project_coordinator/` — review events, panels, marks, and re-review applications (out-of-prose examination subsystem, G11).

## Future Enhancements

- **G5** — Wire stage advancement R1 → R2 → R3: advance `review_milestone` on acceptance and reset `max_tries` per stage. Currently `[Future]`.
- **G9** — Resolve the attempts-exhausted deadlock: at `max_tries == 0`, `reject_submission` raises and the project is stuck `UNDER_VERIFICATION` with no automated escape. The HOD re-review application exists but is not wired to the submission machine `[Planned]`.
