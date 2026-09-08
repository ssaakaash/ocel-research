# Known Gaps and Edge Cases

This document is the authoritative register of unimplemented requirements (`G1`..`G11`) and known edge cases (`E1`..`E15`) for the Educational Capstone Portal backend. Every entry is derived from verified facts about the current codebase. Gaps describe specified-but-absent or divergent behavior; edge cases describe scenarios the implemented system handles ambiguously, unsafely, or not at all. No gaps beyond `G1`..`G11` exist; do not invent new ones.

## Summary Table

| ID | Title | Category | Severity | Status |
|---|---|---|---|---|
| G1 | OCR Service absent | Missing Service | Medium | Planned |
| G2 | Turnitin integration absent | Missing Service | Medium | Planned |
| G3 | Malware & vulnerability scanning absent | Missing Service | High | Planned |
| G4 | `is_editable` + edited-value storage absent | Data Model | Medium | Open |
| G5 | Stage advancement R1→R2→R3 not wired | State Machine | High | Open |
| G6 | Two divergent data models | Migration | High | Open |
| G7 | `REJECTED` resting state is dead code | State Machine | Medium | Open |
| G8 | Faculty-proposal rejection path under-specified | Enforcement | Low | Open |
| G9 | Attempts-exhausted deadlock | State Machine | High | Open |
| G10 | "One team/one idea per student" global guard not located | Enforcement | Medium | Open |
| G11 | Out-of-prose subsystems undocumented in requirements | Enforcement | Low | Open |

## Detailed Gaps

### G1 — OCR Service absent

- **Description:** The requirement "OCR extracts scores automatically" is unimplemented; scoring is manual entry. `[Planned]`
- **Specified vs Implemented:** Specified an OCR Service that auto-extracts scores. Implemented: no OCR code anywhere in the codebase (zero matches); faculty enter scores by hand.
- **Impact:** Manual transcription effort and transcription-error risk for every score; no automation of the scoring step.
- **Affected files:** `app/services/project_service.py` (`add_project_score`), the modular `scores` model under `app/modules/reports/`, `app/routers/faculty.py`.
- **Recommended remediation:** Introduce an OCR Service and a scoring model that captures machine-extracted values distinctly from confirmed values; close `G4` first so extracted values can be corrected without violating immutability.
- **Related diagrams:** [faculty-review-workflow.md](../diagrams/faculty-review-workflow.md).
- **Related edge cases:** `E6` (score immutability vs. editing extracted values).

### G2 — Turnitin integration absent

- **Description:** No Turnitin API client or report parser; faculty type scores and upload report file paths. `[Planned]`
- **Specified vs Implemented:** Specified Turnitin-driven similarity/AI scoring. Implemented: faculty manually enter `ai_percentage` / `similarity_percentage` and supply `ai_report_path` / `similarity_report_path`.
- **Impact:** No automated similarity/AI checking; percentages depend on manual entry and externally produced reports.
- **Affected files:** `app/services/project_service.py`, the modular `scores` model under `app/modules/reports/`, artifact storage via `project_report_artifacts`, `app/routers/faculty.py`.
- **Recommended remediation:** Add a Turnitin Service that submits artifacts and populates percentages; depends on `G4` and resolution of `E6`.
- **Related diagrams:** [faculty-review-workflow.md](../diagrams/faculty-review-workflow.md).
- **Related edge cases:** `E6`, `E12` (null score values accepted).

### G3 — Malware & vulnerability scanning absent

- **Description:** Only zip-bomb, path-traversal, corrupt-ZIP, size, and type validation exist; there is no malware or vulnerability scanning. `[Planned]`
- **Specified vs Implemented:** Specified a "Security Scanner Service." Implemented: inline validation only (`zip_validator` + `UploadService`); the scanner is not a service. Malware scan and vulnerability scan have no implementation.
- **Impact:** Uploaded archives are extracted and compiled in a TeX Live container without content scanning — a direct security exposure.
- **Affected files:** `app/security/zip_validator.py`, `app/modules/reports/services/upload.py`, `app/security/rate_limiter.py`, `app/modules/reports/services/compile.py`.
- **Recommended remediation:** Integrate an out-of-process malware scanner into the upload path with quarantine/reject handling; follow with vulnerability scanning of extracted source.
- **Related diagrams:** [report-processing-pipeline.md](../diagrams/report-processing-pipeline.md).
- **Related edge cases:** `E7` (concurrent upload during PROCESSING), `E8` (enqueue failure after commit).

### G4 — `is_editable` + separate edited-value storage absent

- **Description:** Scores overwrite in place; there is no before/after capture and no score-correction-specific audit fields.
- **Specified vs Implemented:** Specified editable extracted values with stored corrections. Implemented: the new `scores` model has no `is_editable` and no separate edited-value column; values are written once and locked.
- **Impact:** No way to record an extracted-then-corrected value distinctly; blocks safe OCR/Turnitin automation and conflicts with the "faculty may edit values" expectation.
- **Affected files:** the modular `scores` model under `app/modules/reports/`, `app/services/project_service.py` (`add_project_score`).
- **Recommended remediation:** Add editable-value storage and correction audit fields; reconcile with score immutability so corrections are versioned, not overwrites.
- **Related diagrams:** [faculty-review-workflow.md](../diagrams/faculty-review-workflow.md).
- **Related edge cases:** `E6`, `E12`.

### G5 — Stage advancement R1→R2→R3 not wired

- **Description:** `ensure_project_report` always defaults `review_milestone='R1'`; `state.py` never advances the milestone; `max_tries` is not reset per stage.
- **Specified vs Implemented:** Specified a three-stage `R1 → R2 → R3` progression with per-stage attempts. Implemented: every report defaults to `R1` and never advances; attempts are not reset between stages.
- **Impact:** The multi-stage review workflow described by requirements is not enforced end-to-end; stages do not progress automatically.
- **Affected files:** `app/modules/reports/services/state.py`, the `project_reports.review_milestone` header, `app/modules/project_coordinator/`.
- **Recommended remediation:** Wire milestone advancement on acceptance and reset `max_tries` per stage; resolve `G7`/`G9` so transitions are deterministic.
- **Related diagrams:** [submission-stage-workflow.md](../diagrams/submission-stage-workflow.md), [project-lifecycle-state-machine.md](../diagrams/project-lifecycle-state-machine.md).
- **Related edge cases:** `E1` (attempts exhausted), `E15` (cross-model write skew).

### G6 — Two divergent data models

- **Description:** Legacy (`app/models/*`) and new modular (`app/modules/*/models/*`) layers coexist; the live submission machine writes the legacy `Project`, creating drift risk during migration.
- **Specified vs Implemented:** The target is the modular model exposed via `contracts.py`. Implemented: the live state machine in `app/modules/reports/services/state.py` still writes the legacy `Project`, so both layers are active simultaneously.
- **Impact:** Risk of inconsistent reads/writes across model layers during the in-progress migration; behavior depends on which layer a given path touches.
- **Affected files:** `app/models/*`, `app/modules/{project_registration,project_coordinator,reports,venue_booking}/models/*`, `app/modules/reports/services/state.py`, `alembic/` (phase A, phases B/C, reports cutover).
- **Recommended remediation:** Complete the cutover to the modular model and retire legacy writes once parity is verified.
- **Related diagrams:** [domain-model.md](../diagrams/domain-model.md), [submission-state-machine.md](../diagrams/submission-state-machine.md).
- **Related edge cases:** `E15` (cross-model write skew between `Project.max_tries` and `ProjectReportVersion.max_tries`).

### G7 — `REJECTED` resting state is dead code

- **Description:** `reject_submission` sets `NOT_SUBMITTED`, never `REJECTED`; the upload guard accepts `REJECTED` (unreachable). `REJECTED` only appears in `AuditLog.status`.
- **Specified vs Implemented:** `REJECTED` is part of the `submission_status` vocabulary. Implemented: it is never set as a resting state, so the upload guard branch that accepts it is unreachable.
- **Impact:** Misleading state vocabulary; an apparently valid resting state can never occur, complicating reasoning about the machine.
- **Affected files:** `app/modules/reports/services/state.py`.
- **Recommended remediation:** Either set `REJECTED` as a real resting state on rejection or remove it from the vocabulary and the dead upload-guard branch.
- **Related diagrams:** [submission-state-machine.md](../diagrams/submission-state-machine.md).
- **Related edge cases:** `E1` (deadlock interaction with rejection).

### G8 — Faculty-proposal rejection path under-specified

- **Description:** The prose gives only the approve branch; `cancelled` exists in code, but no "notify/unlock team" step is defined.
- **Specified vs Implemented:** Specified: only the faculty-proposal approval flow. Implemented: a `cancelled` status exists for `faculty_project_proposals`, but the rejection-side notification/unlock behavior is undefined.
- **Impact:** Behavior on faculty-proposal rejection is ambiguous; team/notification cleanup is unspecified.
- **Affected files:** `app/modules/project_registration/`.
- **Recommended remediation:** Define the rejection branch end-to-end, including notification and any team-state cleanup.
- **Related diagrams:** [faculty-registration.md](../diagrams/faculty-registration.md).
- **Related edge cases:** `E4` (idea-rejection restart undefined; analogous cleanup ambiguity).

### G9 — Attempts-exhausted deadlock

- **Description:** When `max_tries==0`, `reject_submission` raises; the project is stuck `UNDER_VERIFICATION` with no automated escape. The HOD re-review application exists but is not wired to the submission machine.
- **Specified vs Implemented:** Specified bounded attempts with a resolution path. Implemented: exhausting attempts raises `ValueError` and leaves the submission stuck; re-review applications are not connected to the submission state machine.
- **Impact:** Deadlock — faculty cannot reject and the student cannot resubmit; no automated recovery.
- **Affected files:** `app/modules/reports/services/state.py`, `app/modules/project_coordinator/` (re-review applications).
- **Recommended remediation:** Wire re-review approval to reset/advance the submission machine, or define an explicit escape transition for `max_tries==0`.
- **Related diagrams:** [submission-stage-workflow.md](../diagrams/submission-stage-workflow.md), [submission-state-machine.md](../diagrams/submission-state-machine.md).
- **Related edge cases:** `E1` (attempts-exhausted deadlock).

### G10 — "One team/one idea per student" global guard not located

- **Description:** No global DB uniqueness for one active team/idea per student was located; membership PK `(project_id, student_reg_no)` permits multi-project membership, relying on application-layer checks.
- **Specified vs Implemented:** Specified one active idea and one team per student with lock-on-submit. Implemented: enforcement is application-layer only; the composite PK does not prevent membership in multiple projects.
- **Impact:** A student could be associated with multiple projects/ideas if an application-layer check is missed; no database-level invariant.
- **Affected files:** `app/modules/project_registration/`, `app/shared/models/*`.
- **Recommended remediation:** Add a database-level uniqueness/partial constraint or a verified centralized guard for active-team/active-idea membership.
- **Related diagrams:** [student-registration.md](../diagrams/student-registration.md), [domain-model.md](../diagrams/domain-model.md).
- **Related edge cases:** `E2` (unconfirmed members at submit), `E3` (member declines after lock).

### G11 — Out-of-prose subsystems undocumented in requirements

- **Description:** Subsystems exist in code but are undocumented in requirements: review events/panels/marks (examination), venue booking and multi-step approvals, re-review applications, absentee permissions, guide reassignment, guide capacity, visibility locks, programme/course/academic-term structure, and outcome/accreditation artifacts (SDG/outcome plans, poster).
- **Specified vs Implemented:** The requirements prose does not cover these subsystems, yet they are implemented and active.
- **Impact:** Significant functionality is undocumented, raising onboarding and maintenance risk and leaving behavior unverified against requirements.
- **Affected files:** `app/modules/project_coordinator/`, `app/modules/venue_booking/`, `app/shared/models/*`, `app/modules/project_registration/`.
- **Recommended remediation:** Bring each subsystem under first-class requirement and architecture documentation; verify behavior against documented rules.
- **Related diagrams:** [enterprise-swimlane.md](../diagrams/enterprise-swimlane.md), [executive-overview.md](../diagrams/executive-overview.md), [domain-model.md](../diagrams/domain-model.md).
- **Related edge cases:** `E5` (capacity-overrun swallowed), `E13` (guide reassignment mid-submission), `E14` (faculty who is also admin).

## Edge Cases

| ID | Description | Current behavior | Risk |
|---|---|---|---|
| E1 | Attempts exhausted (`max_tries==0`) | Faculty cannot reject; student cannot resubmit | Deadlock; project stuck `UNDER_VERIFICATION` (see `G9`) |
| E2 | Unconfirmed members at submit | Idea submittable while members `pending`; no DB gate | Teams locked with unconfirmed members |
| E3 | Member declines after team lock | Team not auto-unlocked; `removed` member stays in list | Stale/inconsistent team composition |
| E4 | Idea rejection → "restart" | Whether team lock / member rows are released is undefined | Orphaned locks or member rows |
| E5 | Guide capacity overrun | `ProjectConfirmed` handler swallows decrement `ValueError` (logs warning), confirms anyway | Over-allocation of guides; silent failure |
| E6 | Score immutability vs. editing values | Locked score returns HTTP 400; no edit-request path for scores | Cannot correct extracted values; conflicts with requirement |
| E7 | Concurrent upload during PROCESSING | Blocked by `SELECT … FOR UPDATE` + HTTP 409 | Handled; documented for completeness |
| E8 | Enqueue failure after DB commit | Orphaned `idle` version row; `rollback_after_enqueue_failure` cannot undo committed write | Inconsistent persisted state |
| E9 | Temp workspace missing at submit | `copytree` guarded by `exists()`; paths set null, submission proceeds | Submission with null artifact paths |
| E10 | Concurrent `start_verification` | Non-locking SELECT → race to `UNDER_VERIFICATION` | Duplicate/racing verification transitions |
| E11 | SSE/task metadata TTL (2h) expiry | Stream cannot authenticate stale polling after TTL | Lost real-time status for long-running tasks |
| E12 | Null score values accepted (new schema) | Approve/reject possible without numeric scores | Null write can block a later legitimate score (unique constraint) |
| E13 | Guide reassignment mid-submission | Effect on in-flight verification/locked scores undefined | Undefined ownership of in-flight work |
| E14 | Faculty who is also admin | Can approve own proposal; no conflict-of-interest guard | Self-approval; governance risk |
| E15 | Cross-model write skew during migration | `Project.max_tries` vs `ProjectReportVersion.max_tries` may diverge | Inconsistent attempt counts across model layers (see `G6`) |

## Discrepancy Notes

- **Dead `REJECTED` state (G7):** The `submission_status` vocabulary includes `REJECTED`, but the live machine never sets it as a resting state — `reject_submission` resets to `NOT_SUBMITTED`. The upload guard still accepts `REJECTED`, making that branch unreachable, and `REJECTED` surfaces only in `AuditLog.status`. Documentation and code that imply `REJECTED` is a reachable resting state are inaccurate; treat it as dead until `G7` is resolved.
- **Dual-model drift (G6):** Two model layers are active at once. The new modular model (exposed via `contracts.py`) is the migration target, but the live submission state machine in `app/modules/reports/services/state.py` still writes the legacy `Project`. This split is the root cause of cross-model write skew (`E15`, e.g. `Project.max_tries` vs `ProjectReportVersion.max_tries`) and must be reconciled by completing the cutover and retiring legacy writes.
