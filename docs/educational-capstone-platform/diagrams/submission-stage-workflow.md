# Educational Capstone Portal — Submission Stage Workflow

This diagram shows the three-stage submission lifecycle (R1 → R2 → R3), the retry loop within
each stage, attempt-counter mechanics, and the terminal failure path when all attempts are
exhausted. Stage advancement is a specified requirement; the wiring between milestone completion
and the next stage's activation is currently a Gap in the live state machine implementation.

```mermaid
flowchart TD
    PROJ(["Project Created\nmax_tries = 3 per stage"])

    PROJ --> R1_START

    subgraph R1["Stage R1 — Review Milestone 1\nRequired: Report"]
        direction TB
        R1_START[Student Uploads and Compiles Report\nReview Milestone: R1]
        R1_SUB[Student Submits to Faculty\nsubmission_status: submitted]
        R1_OPEN[Faculty Opens Submission\nsubmission_status: under_verification]
        R1_DEC{"Faculty Decision\non R1 Submission"}
        R1_APP[R1 Approved\nsubmission_status: accepted]
        R1_REJ[R1 Rejected\nsubmission_status reset to not_submitted\nattempts-- · version++]
        R1_EXHAUST["R1 Attempts Exhausted\nmax_tries = 0\nProject Stuck — Gap"]
    end

    R1_START --> R1_SUB --> R1_OPEN --> R1_DEC
    R1_DEC -->|"Approved"| R1_APP
    R1_DEC -->|"Rejected and max_tries > 0"| R1_REJ
    R1_DEC -->|"Rejected and max_tries = 0"| R1_EXHAUST
    R1_REJ -->|"Re-upload for next attempt"| R1_START
    R1_EXHAUST --> STUCK["Terminal Failure\nNo Escape Path Defined — Gap\nManual Intervention Required"]

    R1_APP --> ADV12["Advance to Stage R2\nNew ProjectReport for R2\nmax_tries reset to 3\nGap: advancement not wired in live state machine"]

    ADV12 --> R2_START

    subgraph R2["Stage R2 — Review Milestone 2\nRequired: Updated Report + PPT"]
        direction TB
        R2_START[Student Uploads and Compiles Updated Report\nUpload PPT artifact separately]
        R2_SUB[Student Submits to Faculty]
        R2_OPEN[Faculty Opens Submission]
        R2_DEC{"Faculty Decision\non R2 Submission"}
        R2_APP[R2 Approved]
        R2_REJ[R2 Rejected\nattempts-- · version++]
        R2_EXHAUST["R2 Attempts Exhausted — Gap"]
    end

    R2_START --> R2_SUB --> R2_OPEN --> R2_DEC
    R2_DEC -->|"Approved"| R2_APP
    R2_DEC -->|"Rejected and max_tries > 0"| R2_REJ
    R2_DEC -->|"Rejected and max_tries = 0"| R2_EXHAUST
    R2_REJ -->|"Re-upload"| R2_START
    R2_EXHAUST --> STUCK

    R2_APP --> ADV23["Advance to Stage R3\nNew ProjectReport for R3\nmax_tries reset to 3\nGap: advancement not wired in live state machine"]

    ADV23 --> R3_START

    subgraph R3["Stage R3 — Review Milestone 3\nRequired: Final Report + PPT + Source Code"]
        direction TB
        R3_START[Student Uploads Final Report and Source ZIP\nUpload PPT artifact separately]
        R3_SUB[Student Submits to Faculty]
        R3_OPEN[Faculty Opens Submission]
        R3_DEC{"Faculty Decision\non R3 Submission"}
        R3_APP[R3 Approved\nFinal acceptance]
        R3_REJ[R3 Rejected\nattempts-- · version++]
        R3_EXHAUST["R3 Attempts Exhausted — Gap"]
    end

    R3_START --> R3_SUB --> R3_OPEN --> R3_DEC
    R3_DEC -->|"Approved"| R3_APP
    R3_DEC -->|"Rejected and max_tries > 0"| R3_REJ
    R3_DEC -->|"Rejected and max_tries = 0"| R3_EXHAUST
    R3_REJ -->|"Re-upload"| R3_START
    R3_EXHAUST --> STUCK

    R3_APP --> FINAL["Project Finalized\nScores locked for all stages\nProject locked — no further submissions\nAll records immutable"]

    STUCK --> STUCK_NOTE["Recommended Escape:\nRe-review Application to HOD\nNot yet wired to submission machine — Gap"]

    classDef stageStyle fill:#003566,stroke:#001d3d,color:#cce5ff
    classDef termStyle fill:#198754,stroke:#157347,color:#ffffff
    classDef failStyle fill:#dc3545,stroke:#b02a37,color:#ffffff
    classDef gapStyle fill:#fd7e14,stroke:#d96a0b,color:#000000
    classDef projStyle fill:#0a0a2a,stroke:#0d6efd,color:#ffffff
    classDef decStyle fill:#6f42c1,stroke:#59359a,color:#ffffff
    classDef advStyle fill:#495057,stroke:#343a40,color:#ffffff

    class PROJ projStyle
    class FINAL termStyle
    class STUCK,STUCK_NOTE failStyle
    class R1_EXHAUST,R2_EXHAUST,R3_EXHAUST,ADV12,ADV23 gapStyle
    class R1_DEC,R2_DEC,R3_DEC decStyle
    class R1_APP,R2_APP,R3_APP stageStyle
```

---

## Notes

- **Three stages map to `review_milestone ∈ {R1, R2, R3}`** on the `project_reports` table. Each
  stage has its own `ProjectReport` row (unique per `project_id, review_milestone`).
- **Stage advancement is a Gap**: the `ProjectReport` data model supports R1/R2/R3 as distinct
  rows, but the live state machine (`reports/services/state.py`) always defaults
  `review_milestone = 'R1'` and never advances the milestone. Milestone advancement must be
  wired to the `accept_submission` path.
- **Attempt counter (`max_tries`) is per version record** on `ProjectReportVersion`. It starts
  at 3 and is decremented on each faculty rejection. It is not reset automatically when a new
  stage begins (this reset must be implemented alongside stage advancement).
- **Source code for R3**: the spec requires source code as a deliverable for Stage 3. In the
  current model, source code is the uploaded ZIP itself (`zip_path` on the version record).
  There is no dedicated `source_code` artifact type — the `project_report_artifacts` table
  supports `ppt`, `poster`, `sdg_plan`, `outcome_plan`, `outcome_status`,
  `outcome_attainment_proof` but not `source_code`.
- **PPT for R2 and R3**: PPT is uploaded as a `ProjectReportArtifact` with
  `artifact_type = 'ppt'`. The uniqueness constraint `(report_version_id, artifact_type)`
  ensures one PPT per version.
- **Free compile retries**: the attempt counter is only decremented on faculty rejection.
  Compilation failures (LaTeX errors) are free retries with no attempt consumed.

---

## Business Rules

- Maximum **3 faculty-rejection attempts per stage** (`max_tries = 3` on `ProjectReportVersion`).
- Each faculty rejection: `max_tries -= 1`, `version += 1`, `submission_status → NOT_SUBMITTED`,
  `compilation_status → IDLE`.
- `reject_submission` raises `ValueError: Student has exhausted all 3 compilation attempts`
  if `max_tries ≤ 0`, leaving the project stuck in `UNDER_VERIFICATION`.
- `accept_submission` and `reject_submission` are both gated on
  `submission_status == UNDER_VERIFICATION`; any other state raises an error.
- `start_verification` (faculty opening) is gated on `submission_status == SUBMITTED`.
- Compilation can only start when `submission_status == NOT_SUBMITTED` (compile is blocked if
  a prior submission is pending review or accepted).
- Stage 1 artifact: compiled report PDF (in ZIP). Stage 2 adds PPT. Stage 3 adds source ZIP.

---

## Edge Cases

- **`max_tries == 0` deadlock**: the faculty cannot reject (exception thrown), the student
  cannot resubmit (submission is `UNDER_VERIFICATION`). The project is permanently stuck unless
  a manual database update or a re-review application mechanism (not yet wired) is invoked.
- **Stage advancement not implemented**: if R1 is accepted, no automatic mechanism advances the
  project to R2. The student would need to manually trigger R2 — the exact mechanism is
  undefined in the current codebase.
- **Version counter in legacy vs. new model**: the legacy `Project.version` (monotonic per
  project) differs from `ProjectReportVersion.version` (monotonic per `ProjectReport`). Both
  are incremented on rejection but may drift if not kept in sync during migration.
- **Accepted stage re-opened**: once `submission_status == ACCEPTED`, no guard prevents an
  admin from manually resetting the status via the admin service — there is no database-level
  immutability.
