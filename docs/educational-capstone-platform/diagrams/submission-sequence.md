# Educational Capstone Portal — Submission Sequence Diagram

This sequence diagram traces the complete message flow for a single report submission cycle:
upload, validation, compilation, student preview loop, faculty review, score entry, and the
approve/reject decision paths. Future participants (Turnitin, OCR Service) are included to
document the intended architecture alongside the current manual implementation.

```mermaid
sequenceDiagram
    autonumber

    participant S as Student
    participant P as Portal API
    participant V as ZIP Validator
    participant W as Celery Worker
    participant F as Faculty
    participant A as Audit Service
    participant T as "Turnitin [Planned]"
    participant O as "OCR Service [Planned]"

    Note over S,A: ── Upload and Validation Phase ──

    S->>P: POST /upload {ZIP file, project_id}
    activate P

    P->>P: Rate limit check — per student_id via Redis
    P->>P: Check submission_status in NOT_SUBMITTED or REJECTED
    P->>P: Check compilation_status not PROCESSING

    P->>V: validate(file)
    activate V
    V->>V: Check file extension — must be .zip
    V->>V: Check compressed size — against MAX_COMPRESSED_SIZE_MB
    V->>V: Check ZIP-bomb decompression ratio
    V->>V: Check path-traversal on all entries
    V->>V: Check for corrupt or invalid ZIP archive

    Note over V,O: Malware scan and vulnerability scan not implemented — Gap

    alt Validation Failed
        V-->>P: Validation error — type, size, bomb, or traversal
        deactivate V
        P-->>S: HTTP 400 or 413 — Upload Rejected
        P->>A: log action=UPLOAD_FAILED project_id version
    else Validation Passed
        V-->>P: OK — file is safe
        deactivate V

        P->>P: Compute SHA-256 content hash
        P->>P: Check cache — prior compilation for this hash?

        alt Cache Hit — same ZIP as prior successful compile
            P-->>S: HTTP 200 — Prior compilation result reused
            Note over S: Student may preview existing PDF
        else Cache Miss — new or changed ZIP
            P->>P: Save ZIP to temp workspace — task_uuid as key
            P->>P: Create ProjectReportVersion record — compilation_status: idle
            P->>W: Enqueue compilation task — task_uuid, project_id
            P->>P: Store task metadata in Redis — TTL 2 hours
            P-->>S: HTTP 202 Accepted — task_uuid for SSE polling
            P->>A: log action=COMPILATION_STARTED system_actor=CELERY_WORKER
        end
    end
    deactivate P

    Note over S,A: ── Compilation Phase ──

    activate W
    W->>W: Extract ZIP to temp workspace
    W->>W: Run LaTeX compilation pipeline — pdflatex or texlive

    alt Compile Succeeded
        W->>W: Store PDF + log + artifacts in tmp workspace
        W-->>P: SUCCESS — pdf_path, log_path set on version
        W->>A: log action=COMPILATION_SUCCESS status=SUCCESS
        Note over S: Student receives SSE event — compile succeeded
    else Compile Failed
        W-->>P: FAILED — error detail and log
        W->>A: log action=COMPILATION_FAILED status=FAILED
        Note over S: Student receives SSE event — compile failed\nNo attempt consumed — free retry
        S->>P: Edits source and re-uploads ZIP
        Note over S,W: Re-upload triggers the Upload and Validation Phase again
    end
    deactivate W

    Note over S,A: ── Student Preview Loop — Unlimited Re-runs ──

    loop Until Student is satisfied with compiled output
        S->>P: GET /report/preview — retrieve compiled PDF
        P-->>S: PDF artifact for review
        opt Student wants to edit
            Note over S: Student edits LaTeX source
            S->>P: POST /upload — updated ZIP
            Note over S,W: Re-upload triggers full pipeline from step 1
        end
    end

    Note over S,A: ── Submission to Faculty Phase ──

    S->>P: POST /submit {project_id, student_reg}
    activate P
    P->>P: Guard — compilation_status must be SUCCESS
    P->>P: Move files from temp to persistent storage
    P->>P: Set submission_status: submitted — submitted_at recorded
    P->>P: Student edits now locked
    P-->>S: HTTP 200 — Submission confirmed
    P->>A: log action=STUDENT_SUBMITTED student_reg
    P->>F: Notification — new submission awaiting review
    deactivate P

    Note over S,A: ── Faculty Review Phase ──

    F->>P: GET /submission — opens submission
    activate P
    P->>P: Set submission_status: under_verification
    P-->>F: Submission artifacts — PDF, report version, prior scores
    P->>A: log action=FACULTY_STARTED_VERIFICATION faculty_id
    deactivate P

    F->>F: Reviews compiled PDF

    F->>P: POST /upload-turnitin-report {ai_report, similarity_report}
    P-->>F: Report files stored — ai_report_path and similarity_report_path set

    Note over F,O: ── Score Recording — Current vs Planned ──

    rect rgb(255, 243, 205)
        Note over T,O: Planned — not yet implemented
        P-->>T: POST report for plagiarism analysis [Planned]
        T-->>P: similarity_percentage extracted [Planned]
        P-->>O: POST report PDF for OCR parsing [Planned]
        O-->>P: ai_percentage and similarity_percentage extracted [Planned]
        Note over F,O: Faculty may override OCR values — is_editable flag — Gap
    end

    F->>P: POST /score {ai_percentage, similarity_percentage, comment}
    activate P
    P->>P: Guard — SERIALIZABLE transaction
    P->>P: Check — score already exists for this version?

    alt Score already recorded — immutable
        P-->>F: HTTP 400 — Scores are locked for this version
    else First score for this version — accepted
        P->>P: Write Score record — unique per report_version_id and faculty_id
        P-->>F: HTTP 201 — Score recorded
        P->>A: log action=SCORE_RECORDED faculty_id version
    end
    deactivate P

    Note over S,A: ── Faculty Decision Phase ──

    alt Faculty Approves Submission
        F->>P: POST /approve {project_id}
        activate P
        P->>P: Set submission_status: accepted
        P-->>F: HTTP 200 — Submission accepted
        P->>A: log action=FACULTY_ACCEPTED faculty_id
        P->>S: Notification — submission approved
        deactivate P

        alt Stage is R1 or R2
            Note over S,F: Advance to next stage\nGap: milestone advancement not yet wired
        else Stage is R3 — Final
            Note over S,F: Project Finalized — Scores locked — No further submissions
        end

    else Faculty Rejects Submission
        F->>P: POST /reject {project_id, remarks}
        activate P
        P->>P: Guard — submission_status must be UNDER_VERIFICATION

        alt max_tries greater than 0
            P->>P: max_tries-- · version++ · reset to NOT_SUBMITTED and IDLE
            P-->>F: HTTP 200 — Rejection recorded
            P->>A: log action=FACULTY_REJECTED faculty_id remarks
            P->>S: Notification — submission rejected with remarks
            deactivate P
            Note over S: Student may re-upload and resubmit\nAttempts remaining: max_tries

        else max_tries equals 0 — Gap
            P-->>F: HTTP 500 — ValueError raised — no attempts remain
            P->>A: log action=FACULTY_REJECTED attempt_exhausted
            deactivate P
            Note over S,F: Project stuck in UNDER_VERIFICATION\nNo automated escape — manual intervention required
        end
    end
```

---

## Notes

- **Autonumbering** (`autonumber`) is enabled so every message has a reference number for
  documentation purposes.
- **Turnitin and OCR participants** are included inside a `rect rgb(255, 243, 205)` highlight
  block to visually separate planned-but-unimplemented interactions from the live flow. They
  send and receive messages that describe the intended architecture.
- **Score immutability** is enforced at the database level (`SERIALIZABLE` isolation +
  `UNIQUE(report_version_id, faculty_id)`). The sequence shows the guard at step 30–31.
- **The student preview loop** (`loop … end`) is unbounded before the student chooses to
  submit. Each iteration may optionally trigger a full re-upload, which re-enters the Upload
  and Validation Phase from step 1.
- **SSE (Server-Sent Events)**: the Portal pushes real-time compilation status to the student
  via an SSE stream backed by Redis. Task metadata (keyed `task:{uuid}:meta`) expires after 2
  hours. This is shown implicitly in the "Compile Succeeded / Failed" Notes.
- **Audit Service** is not a separate process — it is the `AuditLog` table written within the
  same DB session. It is shown as a separate participant for clarity of responsibility.

---

## Business Rules

- Upload requires: `submission_status ∈ {NOT_SUBMITTED, REJECTED}` AND
  `compilation_status ≠ PROCESSING`. Violating either returns HTTP 400 / 409.
- Submission (`submit_for_review`) requires `compilation_status == SUCCESS`; any other state
  raises `ValueError`.
- Faculty review open (`start_verification`) requires `submission_status == SUBMITTED`.
- Faculty accept/reject both require `submission_status == UNDER_VERIFICATION`.
- Score write uses a `SERIALIZABLE` transaction; the second write for the same version raises
  a unique constraint violation (HTTP 400).
- Faculty reject with `max_tries ≤ 0` raises `ValueError` — the endpoint returns 500 in the
  current implementation (no explicit HTTP error mapping for this case).
- All state transitions emit an `AuditLog` entry with `action`, `status`, and the relevant
  actor (`student_reg`, `faculty_id`, or `system_actor`).

---

## Edge Cases

- **Enqueue failure after DB commit (step 13)**: Redis may be unavailable after the
  `ProjectReportVersion` row is committed. The version row persists in an orphaned `idle`
  state. `rollback_after_enqueue_failure` attempts cleanup but cannot undo a committed write.
- **Concurrent faculty open (race at step 22)**: two faculty members calling `start_verification`
  simultaneously on a `SUBMITTED` submission may both pass the guard. No `SELECT FOR UPDATE`
  is used at this transition — a race condition exists.
- **SSE token expiry (step 15)**: if the student's SSE polling begins more than 2 hours after
  the upload, the Redis task metadata has expired and the SSE connection cannot be authenticated.
- **Null score values accepted**: the new `Score` model allows nullable `ai_percentage` and
  `similarity_percentage`. A faculty member can approve or reject without ever entering scores.
- **`REJECTED` resting state unreachable (step 36)**: the upload guard permits re-upload when
  `submission_status == REJECTED`, but `reject_submission` sets `NOT_SUBMITTED`, never
  `REJECTED`. This guard branch is dead code in the current implementation.
