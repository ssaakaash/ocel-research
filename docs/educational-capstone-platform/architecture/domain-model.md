# Domain Model

The Educational Capstone Portal domain model captures the entities, relationships, and invariants that govern capstone-project management: students and faculty, the two registration paths that produce a `Project`, the report-and-version submission records, scoring, and the supporting audit trail. The portal is mid-migration between two coexisting model layers (legacy `app/models/*` and the new modular `app/modules/**/models/*`), so this document enumerates the canonical entities and flags where the two layers diverge `[GAP]` (G6).

## Purpose

Define the persistent data entities of the Educational Capstone Portal, their key columns and constraints, and the invariants the application relies on, so contributors can reason about ownership, cardinality, and lifecycle without re-deriving the schema from source.

## Scope

In scope: the core principal entities (students, faculty, faculty roles), the registration entities (student ideas and members, faculty proposals, projects and members), the submission entities (report headers, report versions, artifacts), scoring, audit, and guide-capacity. A secondary group covers the project-coordinator (examination) and venue-booking subsystems that exist in code but sit outside the original prose requirements (G11).

Out of scope: workflow mechanics and transition guards (see [Project Registration](project-registration.md) and the [Submission System](submission-system.md)), and the wire/API representation of these entities.

## Responsibilities

The domain model is responsible for representing system state durably and enforcing structural invariants through database constraints (CHECK constraints, unique constraints, foreign keys), while leaving behavioral rules to the service layer.

### Core Entities

Principal and identity entities:

- **Student** — table `students`, PK `reg_no`. Authenticates via Google OAuth. Owns ideas and team memberships.
- **Faculty** — table `faculty`, PK `id`. Google OAuth. Holds one or more `FacultyRole` rows.
- **FacultyRole** — table `faculty_roles`. `role_type` CHECK-constrained to `'hod' | 'dean' | 'project_coordinator' | 'panel_member' | 'guide'`; `status ∈ {active, inactive}`; scoped by `school_id`, `department_id`, `programme_code`. One faculty may hold several roles.

Registration entities:

- **StudentProjectIdea** — table `student_project_ideas`. `status`: `pending → approved | rejected | converted_to_project`. Column `converted_project_id` (nullable FK to the resulting project).
- **IdeaMember** — table `student_project_idea_members`. `member_role ∈ {leader, member}`; `confirmation_status`: `pending → confirmed | removed`; `responded_at` (set when non-pending).
- **FacultyProjectProposal** — table `faculty_project_proposals`. `status`: `open → closed | converted_to_project | cancelled`; `max_team_size` constrained `>0 AND <=10`.
- **Project** — table `projects`. `registration_source ∈ {faculty_proposal, student_idea, manual}`; `project_type ∈ {ug, pg, integrated_pg}` (nullable). This is the registration-side project record. Note: the **live submission state machine writes the legacy `Project`** (G6).
- **ProjectMember** — table `student_project`. Composite PK `(project_id, student_reg_no)`; `role ∈ {leader, member}`; `confirmation_status ∈ {pending, confirmed}`.

Submission entities:

- **ProjectReport** — table `project_reports`. `review_milestone ∈ {R1, R2, R3}` (the three Stages); unique `(project_id, review_milestone)`; `current_version`.
- **ReportVersion** — table `project_report_versions`. `compilation_status ∈ {idle, processing, success, failed}`; `submission_status ∈ {not_submitted, submitted, under_verification, accepted, rejected}`; `max_tries` (default 3); `version ≥ 1`; unique `(report_id, version)`.
- **ReportArtifact** — table `project_report_artifacts`. `artifact_type ∈ {ppt, poster, sdg_plan, outcome_plan, outcome_status, outcome_attainment_proof}`; unique `(report_version_id, artifact_type)`. There is **no `source_code` and no `final_report` artifact type**: source code is the version `zip_path` and the report is the version `pdf_path`.
- **Score (new)** — table `scores`. Unique `(report_version_id, faculty_id)`; `ai_percentage` / `similarity_percentage` are `[0,100]` or NULL; `ai_report_path`, `similarity_report_path`, `comment`. **No `is_editable` column and no separate edited-value column** `[GAP]` (G4).
- **Score (legacy)** — table `scores` (legacy layer). Unique `(project_id, version)`; `ai_percentage` / `similarity_percentage` constrained `[0,100]`; `flag`.
- **AuditLog** — table `audit_log`. Receives a row on every state transition; carries a `status` field and a `system_actor` (e.g. `CELERY_WORKER`).
- **FacultyGuideCapacity** — table `faculty_guide_capacity`, keyed per `(faculty_id, academic_year, project_type)`.

### Relationships

- A **Student** owns zero or more **StudentProjectIdea** rows and participates in **ProjectMember** / **IdeaMember** rows.
- A **StudentProjectIdea** has many **IdeaMember** rows (one flagged `leader`) and, when approved, references one **Project** via `converted_project_id`.
- A **FacultyProjectProposal** converts into one **Project** (`registration_source='faculty_proposal'`).
- A **Project** has many **ProjectMember** rows and many **ProjectReport** rows (one per `review_milestone`).
- A **ProjectReport** has many **ReportVersion** rows (monotonic `version`); each **ReportVersion** has up to one artifact per `artifact_type` and (new layer) up to one **Score** per faculty.
- A **Faculty** holds many **FacultyRole** rows and (as guide) owns **FacultyGuideCapacity** rows and authors **Score** rows.

See the entity-relationship diagram for cardinality.

### Ownership

- A **Student** owns their ideas and is the subject of their team memberships; the **Team Leader** is a `role='leader'` membership value, not a distinct identity.
- A **guide** (faculty role) owns approval/scoring of the projects they supervise and the associated `FacultyGuideCapacity`.
- An **Admin** owns faculty-proposal approval, user CRUD/CSV bulk upload, and per-semester visibility locks (`project_visibility_lock.locked_by`).
- The **Celery worker** (`system_actor='CELERY_WORKER'`) owns compilation-side writes and the resulting `AuditLog` rows.

### Secondary entity group (examination & venue, G11)

These exist in code but lie outside the original prose requirements:

- **ReviewEvent** (`review_events`), **ReviewPanel** (`review_panels`), **ReviewMark** (`review_marks`, `status: draft → confirmed → locked`, unique `(event, student, entered_by)`), **mark edit-request**, **ReReviewApplication** (`rereview_applications`, `pending → approved | rejected`, HOD-decided).
- **Venue** (`venues`, `status: active | maintenance | inactive`), **VenueBooking** (`venue_bookings`, `request_for_booking → confirmed | cancelled | rejected`), **VenueBookingApproval** (`venue_booking_approvals`, ordered `step_no`, `decision: pending → approved | rejected`, `approval_role ∈ {hod, dean, project_coordinator, admin, system}`).
- **VisibilityLock** (`project_visibility_lock`, admin per-semester).

## Workflow References

- Entity-relationship overview: [../diagrams/domain-model.md](../diagrams/domain-model.md)
- Project lifecycle across the entity states: [../diagrams/project-lifecycle-state-machine.md](../diagrams/project-lifecycle-state-machine.md)
- How registration entities are produced: [Project Registration](project-registration.md)
- How report/version/score entities evolve: [Submission System](submission-system.md)

## Business Rules

Structural rules enforced at the data layer:

- StudentProjectIdea invariant: `(status='converted_to_project') = (converted_project_id IS NOT NULL)` — biconditional.
- IdeaMember invariant: a non-`pending` `confirmation_status` implies `responded_at` is set.
- FacultyProjectProposal `max_team_size` is `>0 AND <=10`.
- ProjectMember primary key is `(project_id, student_reg_no)`.
- ProjectReport unique on `(project_id, review_milestone)`; ReportVersion unique on `(report_id, version)` with `version ≥ 1`.
- ReportArtifact unique on `(report_version_id, artifact_type)`.
- Score (new) unique on `(report_version_id, faculty_id)`; Score (legacy) unique on `(project_id, version)`; both constrain percentages to `[0,100]` (new layer also permits NULL).

## Constraints

- All listed state vocabularies are CHECK-constrained unless noted.
- Two model layers coexist; the live submission machine persists to the **legacy** `Project`, while the modular models are the migration target. Cross-layer write skew is possible during migration (E15).
- The `scores` table name is shared between the legacy and new layers with different unique keys; references must be qualified by layer.

## Edge Cases

- **E15** — cross-model write skew during migration (`Project.max_tries` vs `ProjectReportVersion.max_tries`): the two layers can disagree on attempt counters until cutover completes.

## Security Considerations

- Identity entities (`students`, `faculty`, `admins`) are populated via Google OAuth and admin CSV bulk upload; authorization is role-scoped through `FacultyRole` (`school_id`, `department_id`, `programme_code`).
- `AuditLog` provides the tamper-evidence record for every state transition; it carries `system_actor` to distinguish human vs worker writes.
- Score corrections leave no before/after capture in the schema `[GAP]` (G4), limiting forensic reconstruction of edited values.

## Implementation Notes

- Legacy models: `app/models/*` (`Project`, `Score`, `Report`, …) — written by the live machine in `app/modules/reports/services/state.py`.
- Modular models: `app/modules/{project_registration,project_coordinator,reports,venue_booking}/models/*`; modules expose stable interfaces via `contracts.py`.
- Shared identity/audit models: `app/shared/models/*` (students, faculty, faculty_role, audit_log, notifications, programme/course/school/department).
- Schema evolution lives in `alembic/` (phase A, phases B/C, reports cutover).

## Future Enhancements

- **G4** `[Planned]` — add `is_editable` plus separate edited-value storage to `scores` so score corrections capture before/after values and a correction-specific audit trail, rather than overwriting in place.
- **G6** `[Future]` — complete the dual-model migration so a single canonical model backs the submission machine, eliminating legacy/modular drift.
