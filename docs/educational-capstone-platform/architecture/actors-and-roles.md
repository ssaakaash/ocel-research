# Actors and Roles

This document catalogs every actor in Educational Capstone Portal — authenticated principals, faculty roles, and service/system actors — and defines what each may do. It includes a permissions matrix and an approval-powers summary so engineers can reason about authorization without reading the router code.

## Purpose

Define the system's actors and their authority precisely, providing a single authoritative permissions reference. It complements [system-overview.md](system-overview.md) (which describes journeys) by enumerating capabilities per actor.

## Scope

Covers the four principal (authenticated) actor types, the five faculty roles, and the service/system actors. Role values that are not separate identities (notably Team Leader) are documented as role attributes. Detailed transition guards are in [state-machines.md](state-machines.md); this document concerns who may invoke them, not the mechanics.

## Responsibilities

### Student

`students` (PK `reg_no`); authenticates via Google OAuth. Creates ideas (one active idea per student), forms teams, invites and manages members, and uploads/compiles/submits reports for the team's project. A student is bound by application-layer one-team/one-idea constraints (see G10 — no global DB uniqueness located).

### Team Leader

Not a separate identity: a role value (`student_project.role='leader'` / `student_project_idea_member.member_role='leader'`). The leader-only privilege is enforced — `routers/ideas.py` returns HTTP 403 "only the team leader may submit." The leader must be a member of the team.

### Faculty Guide

`faculty` (PK `id`) holding the `guide` role. Approves/rejects student ideas; opens and reviews submissions; accepts/rejects submissions (`accept_submission`/`reject_submission`); records scores (`add_project_score`). Guide assignment is governed by `faculty_guide_capacity` per `(faculty_id, academic_year, project_type)`.

### Admin

`admins` (PK `id`). Approves/rejects faculty proposals (`→ converted_to_project` / `cancelled`); performs user CRUD with CSV bulk upload; sets per-semester visibility locks (`project_visibility_lock`, `locked_by → admin`). A faculty member who is also an admin can approve their own proposal — no conflict-of-interest guard (E14).

### Project Coordinator

Faculty role `project_coordinator`. Schedules review events and panels (`review_events.created_by`), manages marks (`marks_service`), and approves mark edit-requests (`edit_request_service`). Also a venue approval role.

### Panel Member

Faculty role `panel_member`. Enters review marks during examination (`review_marks.entered_by → faculty`). Marks progress `draft → confirmed → locked`; confirmed/locked marks are editable only via an approved edit-request.

### HOD

Faculty role `hod`. Approves/rejects re-review applications (`rereview_applications.hod_id`); approves mark edit-requests; serves as a venue approval role.

### Dean

Faculty role `dean`. Serves as a venue approval role (`venue_booking_approvals.approval_role` includes `dean`). Broader academic authority is [INFERENCE] — not grounded in the codebase beyond the venue-approval capability.

### Service / System Actors

- **Report Processing Service** — Celery worker performing LaTeX compilation and artifact generation; audited as `system_actor="CELERY_WORKER"`.
- **Notification service / event bus** — in-process event bus (`app/shared/events`) and notification writer (`app/shared/notifications/writer.enqueue`).
- **Audit logger** — writes an `AuditLog` row on every state transition.
- **Redis** — rate limiting, task metadata, and SSE backing.
- **Security Scanner Service** — not a standalone service; inline validation only (`app/security/zip_validator.py` + `UploadService`) covering zip-bomb, path-traversal, corrupt-ZIP, type, size, and rate limit. Malware/vulnerability scanning is absent ([GAP] G3).
- **OCR Service** — [GAP] G1, [Planned]; no implementation.
- **Turnitin Service** — [GAP] G2, [Planned]; faculty enter scores manually and upload report file paths.

### Permissions Matrix

Cells are `Yes` / `No` / `[INFERENCE]`. Capabilities not bound to a specific role in the grounded facts are marked `[INFERENCE]`.

| Actor | Create Idea | Submit Idea | Create Proposal | Approve Idea | Approve Proposal | Open/Review Submission | Accept/Reject Submission | Record Score | Enter Marks | Approve Edit-Request | Approve Re-review | User CRUD | Visibility Lock | Venue Approval |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Student | Yes | No | No | No | No | No | No | No | No | No | No | No | No | No |
| Team Leader | Yes | Yes | No | No | No | No | No | No | No | No | No | No | No | No |
| Faculty Guide | No | No | [INFERENCE] | Yes | No | Yes | Yes | Yes | No | No | No | No | No | No |
| Project Coordinator | No | No | [INFERENCE] | No | No | No | No | No | No | Yes | No | No | No | Yes |
| Panel Member | No | No | [INFERENCE] | No | No | No | No | No | Yes | No | No | No | No | No |
| HOD | No | No | [INFERENCE] | No | No | No | No | No | No | Yes | Yes | No | No | Yes |
| Dean | No | No | [INFERENCE] | No | No | No | No | No | No | No | No | No | No | Yes |
| Admin | No | No | No | No | Yes | No | No | No | No | No | No | Yes | Yes | Yes |

Notes:

- **Create Proposal** is a faculty capability (`faculty_project_proposals`); the grounded facts attribute proposal authorship to faculty generally and do not bind it to a specific role, hence `[INFERENCE]` for the faculty-role rows.
- **Venue Approval** corresponds to `venue_booking_approvals.approval_role ∈ {hod, dean, project_coordinator, admin, system}`.
- **Enter Marks** (`review_marks.entered_by`) is performed by the panel member/examiner; the project coordinator manages and schedules marks but is not the grounded entrant.

### Approval Powers

- **Idea approval** — Guide approves/rejects student ideas (`→ converted_to_project` / `rejected`).
- **Proposal approval** — Admin approves/rejects faculty proposals (`→ converted_to_project` / `cancelled`).
- **Submission decisions** — Guide accepts/rejects submissions (only when `UNDER_VERIFICATION`); each rejection consumes one attempt (`max_tries−−`, `version++`).
- **Mark edit-requests** — Project Coordinator and HOD approve mark edit-requests; an approved request is required to edit confirmed/locked marks.
- **Re-review applications** — HOD approves/rejects (`rereview_applications.status: pending → approved | rejected`).
- **Venue booking approvals** — HOD, Dean, Project Coordinator, and Admin act as ordered approval roles (`step_no`); decisions are `pending → approved | rejected`.
- **Dean** — beyond venue approval, broader academic authority is [INFERENCE].

## Workflow References

- Actor lanes (Student/Faculty/Admin/Portal/Processing): [../diagrams/enterprise-swimlane.md](../diagrams/enterprise-swimlane.md).
- Registration approvals: [../diagrams/student-registration.md](../diagrams/student-registration.md), [../diagrams/faculty-registration.md](../diagrams/faculty-registration.md).
- Review and decision flow: [../diagrams/faculty-review-workflow.md](../diagrams/faculty-review-workflow.md).
- Related documents: [project-registration.md](project-registration.md), [faculty-review.md](faculty-review.md), [security-model.md](security-model.md).

## Business Rules

- Only the team leader may submit the idea (HTTP 403 otherwise).
- Guide assignment respects `faculty_guide_capacity` per `(guide, academic_year, project_type)`, decremented on `ProjectConfirmed`.
- Faculty roles are CHECK-constrained to `'hod' | 'dean' | 'project_coordinator' | 'panel_member' | 'guide'`, with `status ∈ {active, inactive}`, scoped by `school_id`, `department_id`, `programme_code`.
- A faculty member may hold multiple roles simultaneously.
- Confirmed/locked review marks are editable only via an approved edit-request.

## Constraints

- Team Leader is a stored role value, not a distinct account; authorization checks read the role rather than a separate identity.
- Faculty role authority is scoped (`school_id`, `department_id`, `programme_code`); cross-scope authority is not granted by holding a role generally.
- Service actors act under fixed `system_actor` identities in the audit log (e.g., `CELERY_WORKER`).

## Edge Cases

- **E5** A guide may be over-allocated: the `ProjectConfirmed` handler swallows the capacity-decrement `ValueError` and confirms anyway.
- **E13** Guide reassignment mid-submission has undefined effect on in-flight verification and locked scores.
- **E14** A faculty member who is also an admin can approve their own proposal — no conflict-of-interest guard.

## Security Considerations

All principal actors authenticate via Google OAuth with JWT (`app/shared/auth/{service,deps}.py`); authorization dependencies enforce role and ownership checks at the router boundary. Role scoping (`school_id`, `department_id`, `programme_code`) limits the reach of faculty authority. Admin user CRUD and CSV bulk upload are privileged operations and should be audited closely. There is no conflict-of-interest separation between the admin and faculty identities of the same person (E14).

## Implementation Notes

- Authentication and authorization: `app/shared/auth/service.py`, `app/shared/auth/deps.py`.
- Actor and role models: `app/shared/models/*` (students, faculty, faculty_role, audit_log, notifications).
- Idea/proposal flows and leader enforcement: `app/modules/project_registration/`, `app/routers/ideas.py`.
- Review roles and marks: `app/modules/project_coordinator/` (review events/panels/marks, edit-requests, re-review).
- Venue approval roles: `app/modules/venue_booking/`.
- Admin operations: `app/services/admin_service.py`.

## Future Enhancements

- **G11** [GAP] Several role-driven subsystems (review events/panels/marks, venue booking and multi-step approvals, re-review applications, absentee permissions, guide reassignment, guide capacity, visibility locks) exist in code but are out of the original prose requirements and need first-class documentation and role-permission specification.
- Dean authority beyond venue approval ([INFERENCE]) should be formally specified rather than inferred.
- Conflict-of-interest separation for combined admin/faculty identities (E14) is a candidate hardening.
