# Project Registration

Project registration is the formation phase that produces a `Project` record through one of two initiation paths — a student-initiated idea or a faculty-initiated proposal — and converts the approved formation artifact into a project that the submission system can act on. The two paths differ chiefly in who approves them and whether a member-confirmation handshake applies.

## Purpose

Document both registration paths end to end: how a `Project` is created, how `registration_source` records its provenance, how guide capacity participates, and how team membership is confirmed and locked.

## Scope

In scope: the student-initiated path (idea → team → confirm → guide decision), the faculty-initiated path (proposal → admin decision), the convert-to-project step shared by both, `registration_source`, guide capacity decrement, and the member-confirmation handshake.

Out of scope: report upload, compilation, review, and scoring (see [Submission System](submission-system.md)); entity column details (see [Domain Model](domain-model.md)).

## Responsibilities

Registration owns the formation lifecycle up to and including project creation, after which the submission system takes over.

### Student-Initiated Path

A student creates a `StudentProjectIdea` (`status='pending'`), forms a team by adding `IdeaMember` rows, and the team leader submits the idea. The assigned **guide** then approves or rejects:

- **Approve** → idea `status='converted_to_project'`, `converted_project_id` set; fires the `ProjectConfirmed` event; decrements guide capacity; sends notifications.
- **Reject** → idea `status='rejected'`; the prose calls for discard and restart, though the precise release of the team lock and member rows on restart is undefined (E4).

### Faculty-Initiated Path

A faculty member opens a `FacultyProjectProposal` (`status='open'`, `max_team_size` in `(0,10]`). An **Admin** then decides:

- **Approve** → proposal `status='converted_to_project'`; a `Project` is created with `registration_source='faculty_proposal'`.
- **Reject** → proposal `status='cancelled'`. The rejection branch is under-specified in the prose — `cancelled` exists in code but the notify/unlock-team step is not defined `[GAP]` (G8).

This path has **no member-confirmation handshake**.

### Convert-to-Project

Both paths converge on conversion: the approved formation artifact transitions to `converted_to_project` and a `Project` row is created. The student-idea invariant `(status='converted_to_project') = (converted_project_id IS NOT NULL)` ties the idea to its project biconditionally.

### registration_source

`projects.registration_source ∈ {faculty_proposal, student_idea, manual}` records provenance. `student_idea` and `faculty_proposal` correspond to the two paths above; `manual` covers administrative direct creation.

### Guide Capacity

`FacultyGuideCapacity` is keyed per `(faculty_id, academic_year, project_type)`. On `ProjectConfirmed`, the handler decrements the guide's capacity for the matching key.

### Member Confirmation Handshake

On the student-idea path, each `IdeaMember` moves `pending → confirmed | removed`, and a non-`pending` status sets `responded_at`. The handshake is application-layer; there is no DB gate forcing all members to confirm before submission (E2). The faculty-proposal path skips the handshake entirely.

## Workflow References

- Student path: [../diagrams/student-registration.md](../diagrams/student-registration.md)
- Faculty path: [../diagrams/faculty-registration.md](../diagrams/faculty-registration.md)
- Full project lifecycle (formation through R1/R2/R3): [../diagrams/project-lifecycle-state-machine.md](../diagrams/project-lifecycle-state-machine.md)
- Downstream entity definitions: [Domain Model](domain-model.md)
- Downstream submission behavior: [Submission System](submission-system.md)

## Business Rules

- One active idea per student and one team per student; the team locks on submit. Enforcement is application-layer — no global DB uniqueness was located `[GAP]` (G10).
- Only the team leader may submit the idea; non-leaders receive HTTP 403 ("only the team leader may submit").
- The leader must be a member of the team.
- Team size must not exceed `max_team_size` (≤ 10).
- Guide capacity is decremented per `(guide, academic_year, project_type)` on `ProjectConfirmed`.
- The member-confirmation handshake (`pending → confirmed | removed`) applies only to the student-idea path; the faculty-proposal path has no handshake.

## Constraints

- `FacultyProjectProposal.max_team_size` is `>0 AND <=10`.
- `ProjectMember` PK is `(project_id, student_reg_no)`, which by itself permits a student to belong to multiple projects (see G10).
- Capacity decrement failure is non-fatal: the `ProjectConfirmed` handler swallows the decrement `ValueError`, logs a warning, and confirms anyway (E5).

## Edge Cases

- **E2** — unconfirmed members at submit: an idea is submittable while members are still `pending`; there is no DB gate.
- **E3** — member declines after team lock: the team is not auto-unlocked; the `removed` member remains in the listing.
- **E4** — idea rejection → "restart": whether the team lock and member rows are released is undefined.
- **E5** — guide capacity overrun: the `ProjectConfirmed` handler swallows the decrement `ValueError` and confirms anyway, allowing over-allocation.
- **E14** — faculty who is also admin: such a user can approve their own proposal; there is no conflict-of-interest guard.

## Security Considerations

- Leader-only submission is enforced at the router layer (HTTP 403 otherwise); membership and role checks are application-layer.
- The faculty-equals-admin self-approval path (E14) is an authorization gap with no segregation-of-duties control.
- Every formation transition (idea submit, guide decision, admin decision, conversion) writes an `AuditLog` row.

## Implementation Notes

- `app/modules/project_registration/` — ideas, proposals, capacity, reassignment; `events.py` defines `ProjectConfirmed` and `GuideReassigned`.
- Leader-only submission guard: `app/routers/ideas.py` (HTTP 403).
- `app/services/admin_service.py` — admin proposal approval and project administration.
- `app/shared/events/` — in-process event bus delivering `ProjectConfirmed`; `app/shared/notifications/writer.py` — notification enqueue.

## Future Enhancements

- **G8** `[Planned]` — fully specify the faculty-proposal rejection branch: define the notify/unlock-team behavior accompanying the existing `cancelled` status.
- **G10** `[Planned]` — add a global "one team / one idea per student" guard at the data layer rather than relying solely on application-layer checks.
- **G11** `[Future]` — document and integrate the guide-reassignment and per-semester visibility-lock subsystems (`GuideReassigned`, `project_visibility_lock`) that exist in code but are absent from the original requirements; guide reassignment mid-submission currently has undefined effects on in-flight verification and locked scores (E13).
