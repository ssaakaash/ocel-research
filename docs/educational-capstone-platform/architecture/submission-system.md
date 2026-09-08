# Submission System

The submission system governs how a project's report progresses from an uploaded ZIP through validation, asynchronous LaTeX compilation, leader submission, faculty review, and an accept/reject decision. It is implemented as a dual-axis state machine (`compilation_status` × `submission_status`) that, in the live codebase, persists to the legacy `Project` record (`app/modules/reports/services/state.py`).

## Purpose

Document the live submission state machine: its two status axes, the transitions and guards between states, the attempt accounting, and the surrounding upload, compilation, and review mechanics.

## Scope

In scope: the upload → validation → compilation → submission → verification → decision lifecycle, attempt counters, and the failure/retry behavior of the live machine.

Out of scope: project formation (see [Project Registration](project-registration.md)) and entity schema (see [Domain Model](domain-model.md)).

## Responsibilities

The submission system drives the report through its lifecycle, enforcing each transition's guard and writing an `AuditLog` row on every transition. The two axes are `compilation_status: IDLE → PROCESSING → SUCCESS | FAILED` and `submission_status: NOT_SUBMITTED → SUBMITTED → UNDER_VERIFICATION → ACCEPTED | REJECTED`.

### Upload Lifecycle

`UploadService.accept_upload` saves the ZIP, creates a new `ProjectReportVersion`, and resets compilation to `IDLE`. Guard: `submission_status ∈ {NOT_SUBMITTED, REJECTED}` AND `compilation_status ≠ PROCESSING`; `.zip` only; size ≤ `MAX_COMPRESSED_SIZE_MB`; per-student Redis rate-limit; a `SELECT … FOR UPDATE` row lock prevents concurrent upload (409 if PROCESSING). Note that `REJECTED` is accepted by the guard but is unreachable in practice (G7).

### Validation Lifecycle

Validation is inline (no separate service): ZIP extraction is guarded against path-traversal, decompression-bomb, and corrupt-ZIP, plus type and size checks and the rate limit. Malware and vulnerability scanning are absent `[GAP]` (G7 covers dead-state behavior; scanning gaps are tracked under security below).

### Compilation Lifecycle

`start_compilation` moves `IDLE → PROCESSING` and sets the SHA-256 `content_hash`; its guard is `submission_status == NOT_SUBMITTED`. Compilation runs asynchronously on a Celery worker. `compilation_success` → `SUCCESS`; `compilation_failed` → `FAILED` as a **free retry** (no attempt decrement). Content-hash caching reuses a prior compilation when the hash matches.

### Review Lifecycle

After the leader submits, `start_verification` moves `SUBMITTED → UNDER_VERIFICATION`; its guard is `submission_status == SUBMITTED`. This SELECT is non-locking, so concurrent calls can race into `UNDER_VERIFICATION` (E10).

### Acceptance Lifecycle

`submit_for_review` moves to `SUBMITTED`, copies the temp workspace to persistent storage, locks edits, and sets `submitted_at`; its guard is `compilation_status == SUCCESS`. `accept_submission` then moves `UNDER_VERIFICATION → ACCEPTED`; its guard is `submission_status == UNDER_VERIFICATION`. Scoring (`add_project_score`) writes a versioned, immutable Score under a `SERIALIZABLE` transaction; a second write for the same version returns HTTP 400 ("Scores are locked").

### Failure Lifecycle

`reject_submission` requires `UNDER_VERIFICATION` AND `max_tries > 0`; it decrements `max_tries`, increments `version`, and resets to `NOT_SUBMITTED`/`IDLE`. If `max_tries ≤ 0` it raises `ValueError`, leaving the project stuck in `UNDER_VERIFICATION` (E1, G9). The `REJECTED` resting state is dead code: `reject_submission` sets `NOT_SUBMITTED`, never `REJECTED`; `REJECTED` only appears in `AuditLog.status` (G7).

## Workflow References

- Processing pipeline (upload → validation → compile → preview loop → submit): [../diagrams/report-processing-pipeline.md](../diagrams/report-processing-pipeline.md)
- Stage workflow (R1/R2/R3, attempts, terminal failure): [../diagrams/submission-stage-workflow.md](../diagrams/submission-stage-workflow.md)
- Dual-axis state machine (compilation × submission): [../diagrams/submission-state-machine.md](../diagrams/submission-state-machine.md)
- Message flow (upload → compile → review → decision): [../diagrams/submission-sequence.md](../diagrams/submission-sequence.md)

## Business Rules

- Compile only when `NOT_SUBMITTED`.
- Submit only when `compilation_status == SUCCESS`.
- Accept or reject only when `UNDER_VERIFICATION`.
- Maximum 3 attempts per stage (`max_tries` default 3); each faculty rejection consumes one (`max_tries−−`, `version++`).
- Compile failures are free — no attempt decrement.
- Scores are immutable once written (unique constraint + `SERIALIZABLE`); percentages are `[0,100]`.
- Every state transition writes an `AuditLog` row.

## Constraints

- Uploads are `.zip` only, size ≤ `MAX_COMPRESSED_SIZE_MB`, per-student Redis rate-limited, and serialized by a `FOR UPDATE` row lock.
- The live machine writes the **legacy** `Project`; the modular `ProjectReportVersion` mirrors the axes but can diverge during migration (E15).
- Stage advancement R1 → R2 → R3 is not wired: `ensure_project_report` always defaults `review_milestone='R1'`, the machine never advances the milestone, and `max_tries` is not reset per stage `[GAP]` (G5).

## Edge Cases

- **E1** — attempts exhausted (`max_tries == 0`): faculty cannot reject and the student cannot resubmit, producing a deadlock (see G9).
- **E7** — concurrent upload during PROCESSING: blocked by the `FOR UPDATE` lock and a 409 response.
- **E8** — enqueue failure after DB commit: an orphaned `idle` version row remains; `rollback_after_enqueue_failure` cannot undo a committed write.
- **E9** — temp workspace missing at submit: `copytree` is guarded by `exists()`, so paths are set null and submission proceeds.
- **E10** — concurrent `start_verification`: the non-locking SELECT allows a race into `UNDER_VERIFICATION`.
- **E11** — SSE / task-metadata TTL (2h) expiry: the stream cannot authenticate stale polling once metadata expires.
- **E15** — cross-model write skew during migration (`Project.max_tries` vs `ProjectReportVersion.max_tries`).

## Security Considerations

- Inline ZIP validation covers zip-bomb, path-traversal, corrupt-ZIP, type, and size; uploads are rate-limited per student via Redis.
- Malware and vulnerability scanning are absent `[GAP]` (G3); validation does not inspect file contents beyond structural ZIP guards.
- Scoring runs under `SERIALIZABLE` isolation and is write-once; the lack of an edit-request path for scores means a locked score cannot be corrected (E6, G4).
- Every transition is recorded in `AuditLog`, with the Celery worker writing as `system_actor='CELERY_WORKER'`.

## Implementation Notes

- `app/modules/reports/services/state.py` — the submission state machine (legacy `Project`); houses `create_project`, `start_compilation`, `compilation_success`/`compilation_failed`, `submit_for_review`, `start_verification`, `accept_submission`, `reject_submission`.
- `app/modules/reports/services/upload.py` — upload validation and `ProjectReportVersion` creation (`accept_upload`).
- `app/modules/reports/services/compile.py` — LaTeX compilation; `app/modules/reports/services/cache.py` — content-hash caching.
- `app/security/zip_validator.py` — bomb/traversal/corrupt guards; `app/security/rate_limiter.py` — Redis rate limit.
- `app/services/project_service.py` — `add_project_score` (SERIALIZABLE lock).
- `app/tasks/compile_task.py` + `app/workers/{queue_worker,pdflatex_worker}.py` — Celery compilation; `app/routers/stream.py` — SSE status.

## Future Enhancements

- **G5** `[Planned]` — wire stage advancement R1 → R2 → R3: advance `review_milestone` on acceptance and reset `max_tries` per stage rather than defaulting every report to `R1`.
- **G7** `[Future]` — resolve the dead `REJECTED` resting state: either make `reject_submission` use it or remove it from the upload guard and `AuditLog` vocabulary.
- **G9** `[Planned]` — provide an automated escape from the attempts-exhausted deadlock (`max_tries == 0`), wiring the existing HOD re-review application path into the submission machine.
