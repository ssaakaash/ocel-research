# Educational Capstone Portal — Project Lifecycle State Machine

This state diagram covers the complete lifecycle of a Educational Capstone Portal project from initial idea or proposal
creation through the three submission stages to final locking. It uses composite states to group
related sub-states and annotates known gaps where specified transitions are not yet implemented
in the live codebase.

```mermaid
stateDiagram-v2
    direction TB

    [*] --> IdeaCreated : Student creates idea

    state "Student Idea Path" as STUDENT_PATH {
        IdeaCreated --> MembersPending : Leader auto-confirmed
        MembersPending --> MembersPending : Member responds — confirmed or removed
        MembersPending --> TeamLocked : Leader submits idea
        TeamLocked --> PendingGuideReview : Idea sent to selected faculty guide
        PendingGuideReview --> IdeaApproved : Guide approves
        PendingGuideReview --> IdeaRejected : Guide rejects
    }

    IdeaRejected --> [*] : Idea discarded — full restart required

    note right of TeamLocked
        Constraints enforced:
        One idea per student.
        One team per student.
        Only team leader may submit.
        Leader must be in member list.
    end note

    [*] --> ProposalCreated : Faculty creates proposal

    state "Faculty Proposal Path" as FACULTY_PATH {
        ProposalCreated --> ProposalTeamSet : Team leader and members assigned
        ProposalTeamSet --> PendingAdminReview : Proposal submitted for admin review
        PendingAdminReview --> ProposalApproved : Admin approves
        PendingAdminReview --> ProposalCancelled : Admin rejects
    }

    ProposalCancelled --> [*] : Proposal cancelled

    IdeaApproved --> ProjectCreated : ProjectConfirmed event — capacity decremented — members notified
    ProposalApproved --> ProjectCreated : ProjectConfirmed event — capacity decremented — members notified

    state "Stage R1 — Review Milestone 1" as R1 {
        [*] --> R1_Awaiting
        R1_Awaiting --> R1_Submitted : Student submits — compilation_status must be SUCCESS
        R1_Submitted --> R1_UnderReview : Faculty opens — start_verification
        R1_UnderReview --> R1_Accepted : Faculty approves — accept_submission
        R1_UnderReview --> R1_Rejected : Faculty rejects — max_tries > 0
        R1_UnderReview --> R1_Exhausted : Faculty rejects — max_tries = 0 — Gap
        R1_Rejected --> R1_Awaiting : attempts-- · version++ · reset to not_submitted
        R1_Accepted --> [*]
    }

    R1_Exhausted --> TerminalFailure : Project stuck — no escape path — Gap

    note left of R1_Exhausted
        Gap: max_tries = 0 causes
        reject_submission to raise
        ValueError. No automated
        escape. Manual DB fix or
        re-review application needed.
    end note

    ProjectCreated --> R1 : Stage R1 begins

    R1 --> R2 : R1 accepted — advance to R2\nGap: milestone advancement not wired in live state machine

    state "Stage R2 — Review Milestone 2" as R2 {
        [*] --> R2_Awaiting
        R2_Awaiting --> R2_Submitted : Student submits
        R2_Submitted --> R2_UnderReview : Faculty opens
        R2_UnderReview --> R2_Accepted : Faculty approves
        R2_UnderReview --> R2_Rejected : Faculty rejects — max_tries > 0
        R2_UnderReview --> R2_Exhausted : Faculty rejects — max_tries = 0 — Gap
        R2_Rejected --> R2_Awaiting : attempts-- · version++
        R2_Accepted --> [*]
    }

    R2_Exhausted --> TerminalFailure

    R2 --> R3 : R2 accepted — advance to R3\nGap: milestone advancement not wired in live state machine

    state "Stage R3 — Review Milestone 3" as R3 {
        [*] --> R3_Awaiting
        R3_Awaiting --> R3_Submitted : Student submits
        R3_Submitted --> R3_UnderReview : Faculty opens
        R3_UnderReview --> R3_Accepted : Faculty approves
        R3_UnderReview --> R3_Rejected : Faculty rejects — max_tries > 0
        R3_UnderReview --> R3_Exhausted : Faculty rejects — max_tries = 0 — Gap
        R3_Rejected --> R3_Awaiting : attempts-- · version++
        R3_Accepted --> [*]
    }

    R3_Exhausted --> TerminalFailure

    R3 --> Finalized : R3 accepted — all stages complete

    note right of Finalized
        Scores finalized.
        Scores locked — immutable.
        Project locked.
        No further submissions.
        No further score edits.
    end note

    Finalized --> ProjectLocked : All records sealed

    ProjectLocked --> [*] : Terminal — project lifecycle complete

    TerminalFailure --> [*] : Terminal — undefined state — manual intervention required
```

---

## Notes

- **Two independent entry points** (`[*] --> IdeaCreated` and `[*] --> ProposalCreated`) reflect
  the two registration paths; both converge at `ProjectCreated`.
- **`IdeaRejected` is a true terminal**: the entire idea and team composition are discarded.
  Students must restart from scratch. Whether the team lock is released programmatically is
  **not specified** in the current implementation.
- **`ProposalCancelled` is a terminal** for the proposal; it is not defined as a restart for
  the faculty member (they may create a new proposal from the `[*]` initial state).
- **Stage advancement gap (`R1 → R2`, `R2 → R3`)**: the `project_reports` table supports
  `review_milestone ∈ {R1, R2, R3}` as distinct rows, but the live state machine
  (`state.py`) always defaults to `review_milestone = 'R1'` and contains no logic to create
  the next `ProjectReport` row on stage acceptance.
- **`TerminalFailure`**: when `max_tries` reaches 0, `reject_submission` raises a `ValueError`.
  The project is permanently stuck in `UNDER_VERIFICATION`. A `RereviewApplication → HOD`
  pathway exists in the coordinator module but is not connected to the submission state machine.
- **`ProjectLocked`**: represents the hard terminal state after R3 acceptance. In the current
  implementation, this is the absence of any guard-passing transition out of `ACCEPTED` plus
  the score-lock enforced by the `SERIALIZABLE` transaction.

---

## Business Rules

- `IdeaCreated → MembersPending`: leader's `confirmation_status` is immediately set to
  `confirmed`; all other members start as `pending`.
- `TeamLocked`: the student's global "one team" constraint becomes active; they cannot join
  another team until the idea is resolved.
- `PendingGuideReview → IdeaApproved`: fires `ProjectConfirmed` event, decrements guide
  capacity, enqueues notifications for all members.
- `R*_UnderReview → R*_Rejected` requires `max_tries > 0`; raises on `max_tries ≤ 0`.
- `R*_UnderReview → R*_Accepted` and `R*_UnderReview → R*_Rejected` are both gated on
  `submission_status == UNDER_VERIFICATION`.
- Scores are recorded and locked per version before the accept/reject decision; the locked
  score persists even if the submission is later rejected (the version is incremented, so the
  new attempt gets a fresh score slot).
- `ProjectLocked` (Finalized): no system guard currently prevents an admin from manually
  overriding the status via the admin service endpoints.

---

## Edge Cases

- **Concurrent approval of student idea and faculty proposal for the same team**: both paths
  could theoretically create separate `Project` records for overlapping student sets. The
  `student_project` membership uniqueness `(project_id, student_reg_no)` does not prevent a
  student from appearing in two different projects.
- **Guide reassignment at `PendingGuideReview`**: a `GuideReassigned` event exists but its
  interaction with an idea currently awaiting that guide's decision is undefined.
- **Member `removed` after `TeamLocked`**: a member who declines after the team is locked
  has `confirmation_status = removed` but remains in the idea's member list. The downstream
  project creation may include or exclude them depending on service logic.
- **Milestone reset on rejection**: if stage advancement is eventually implemented, the
  `max_tries` counter on the new `ProjectReport` row must be explicitly reset to 3; this is
  not automatic.
