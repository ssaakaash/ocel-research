# System Overview

Educational Capstone Portal is an asynchronous FastAPI backend for managing capstone projects from registration through review and scoring. This document gives the end-to-end system context: how the principal actors interact, how the two registration paths converge on a single project, how reports are compiled and submitted across three stages, and how projects are finalized.

## Purpose

Provide a single high-level reference for the whole system: the actors, the major journeys, the convergence of dual registration onto one project entity, and the compile/submit/review/finalize lifecycle. It orients new engineers before they read the subsystem-specific documents.

## Scope

This document covers the system's actor journeys and processing/review services at a conceptual level. Detailed transition tables live in [state-machines.md](state-machines.md); detailed actor permissions live in [actors-and-roles.md](actors-and-roles.md); subsystem internals live in their respective documents. The legacy and modular model split (G6) is summarized here and detailed in [domain-model.md](domain-model.md).

### Student Journey

A student authenticates via Google OAuth, creates an idea (one active idea per student), forms a team, and invites members who confirm via a `pending → confirmed | removed` handshake. Only the team leader (a `student_project.role='leader'` value) may submit the idea. On submission the team locks; a guide then approves (the idea converts to a project, firing `ProjectConfirmed`) or rejects (the idea is discarded and the student restarts).

### Faculty Journey

Faculty authenticate via Google OAuth and hold one or more roles. A faculty member may publish a proposal (`faculty_project_proposals`, `max_team_size` in 1..10) that an admin approves (converting it to a project) or rejects (`cancelled`). Guides approve/reject ideas, open and review submissions, accept/reject submissions, and record scores. The faculty-proposal path has no member confirmation handshake, unlike the student-idea path.

### Admin Journey

An admin approves faculty proposals, performs user CRUD with CSV bulk upload, and sets per-semester visibility locks (`project_visibility_lock`). An admin who is also faculty can approve their own proposal; there is no conflict-of-interest guard (E14).

### Project Lifecycle

Both registration paths converge on a **Project Created** state with `registration_source ∈ {faculty_proposal, student_idea, manual}`. From there the project proceeds through report compilation and the three submission stages to a locked, finalized state. See [../diagrams/project-lifecycle-state-machine.md](../diagrams/project-lifecycle-state-machine.md).

## Responsibilities

The system is responsible for authenticating principals, registering projects via either path, validating and compiling LaTeX report sources asynchronously, enforcing the submission state machine across stages, capturing faculty review decisions and scores immutably, and auditing every transition.

### Processing Services

The Report Processing Service is a Celery worker that compiles LaTeX sources into PDFs and generates artifacts. Uploads are validated inline (ZIP guards, size, type, rate limit), a new `ProjectReportVersion` is created, and compilation runs asynchronously with real-time status over SSE. Content-hash (SHA-256) caching reuses prior compilations. The compile/preview loop is **unlimited**: compile failures are free and do not consume attempts, so a team may iterate on compilation as many times as needed before submitting.

### Review Services

Guides open submissions for verification, accept or reject them, and record scores. Project coordinators schedule review events and panels and manage marks; panel members enter review marks; HODs approve re-review applications and mark edit-requests. OCR (G1) and Turnitin (G2) integrations are [Planned] and absent — faculty enter scores manually and upload report file paths.

### Scoring Services

Scores are versioned and immutable: a score row is unique per `(report_version_id, faculty_id)` and written under a `SERIALIZABLE` transaction; a second write for the same version returns HTTP 400 "Scores are locked." Percentages are constrained to `[0,100]` or NULL.

## Workflow References

- End-to-end lifecycle across both registration paths to finalization: [../diagrams/executive-overview.md](../diagrams/executive-overview.md).
- Actor lanes (Student/Faculty/Admin/Portal/Processing): [../diagrams/enterprise-swimlane.md](../diagrams/enterprise-swimlane.md).
- Full project lifecycle states: [../diagrams/project-lifecycle-state-machine.md](../diagrams/project-lifecycle-state-machine.md).
- Subsystem documents: [project-registration.md](project-registration.md), [report-processing.md](report-processing.md), [submission-system.md](submission-system.md), [faculty-review.md](faculty-review.md), [scoring-system.md](scoring-system.md).

## Business Rules

- One active idea per student; one team per student; team locks on submit (application-layer enforcement; see G10).
- Only the team leader may submit the idea (HTTP 403 otherwise); the leader must be in the team; team size ≤ `max_team_size` (≤10).
- Student-idea path requires member confirmation; faculty-proposal path does not.
- Compile only when `NOT_SUBMITTED`; submit only when `SUCCESS`; accept/reject only when `UNDER_VERIFICATION`.
- Max 3 attempts per stage; each faculty rejection consumes one (`max_tries−−`, `version++`); compile failures are free.
- Scores are immutable once written; percentages `[0,100]`.
- Every state transition writes an `AuditLog` row.

## Constraints

- The **live** submission state machine writes the legacy `Project` (`app/modules/reports/services/state.py`), even though the modular models are the migration target (G6).
- Uploads accept `.zip` only, ≤ `MAX_COMPRESSED_SIZE_MB`, subject to a per-student Redis rate limit and a row lock (`SELECT … FOR UPDATE`); concurrent upload during `PROCESSING` returns 409.
- Score writes use `SERIALIZABLE` isolation; the uniqueness constraint enforces immutability.

## Edge Cases

- **E5** Guide capacity overrun: the `ProjectConfirmed` handler swallows the decrement `ValueError` and confirms anyway, allowing over-allocation.
- **E7** Concurrent upload during `PROCESSING` is blocked by `FOR UPDATE` + 409.
- **E10** Concurrent `start_verification` uses a non-locking SELECT, so two callers can race into `UNDER_VERIFICATION`.
- **E11** SSE/task metadata TTL (2h) expiry leaves a stream unable to authenticate stale polling.
- **E14** A faculty member who is also an admin can approve their own proposal (no conflict-of-interest guard).

## Security Considerations

Principals authenticate via Google OAuth with JWT session handling (`app/shared/auth/{service,deps}.py`). Uploads pass inline validation for ZIP-bombs, path traversal, corrupt archives, type, and size, plus a Redis rate limit (`app/security/zip_validator.py`, `rate_limiter.py`). Responses carry security headers (HSTS, X-Content-Type-Options, CSP) via `SecurityHeadersMiddleware` in `app/main.py`. Malware and vulnerability scanning are absent ([GAP] G3).

## Implementation Notes

- Submission state machine: `app/modules/reports/services/state.py` (writes legacy `Project`).
- Upload and version creation: `app/modules/reports/services/upload.py`.
- Compilation and caching: `app/modules/reports/services/compile.py`, `cache.py`.
- Scoring: `app/services/project_service.py` (`add_project_score`, SERIALIZABLE lock).
- Registration, capacity, events: `app/modules/project_registration/` (`events.py`: `ProjectConfirmed`, `GuideReassigned`).
- Review/examination: `app/modules/project_coordinator/`.
- Cross-cutting: `app/shared/auth/`, `app/shared/events/`, `app/shared/notifications/writer.py`, `app/main.py`.

## Future Enhancements

- **G5** [GAP] Stage advancement R1→R2→R3 is not wired: `ensure_project_report` always defaults `review_milestone='R1'`, `state.py` never advances the milestone, and `max_tries` is not reset per stage. Wiring stage progression is required to make the three-stage lifecycle operate end-to-end.
- **G6** [GAP] The two divergent data models (legacy vs modular) must be reconciled; the live machine should migrate from the legacy `Project` onto the modular models to eliminate drift risk.
- OCR (G1) and Turnitin (G2) integrations remain [Planned].
