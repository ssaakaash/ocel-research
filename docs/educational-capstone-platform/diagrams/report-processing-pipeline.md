# Educational Capstone Portal — Report Processing Pipeline

This diagram details the complete technical pipeline that a student report traverses from ZIP
upload through security validation, LaTeX compilation, artifact generation, and the student
preview-edit loop before final submission to faculty. Future and unimplemented security checks
are marked explicitly.

```mermaid
flowchart TD
    START([Student Initiates Upload\nMust be Team Member of the Project])

    START --> GUARD{"submission_status\nin NOT_SUBMITTED\nor REJECTED?\ncompilation_status\nnot PROCESSING?"}
    GUARD -->|"No — invalid state"| SBLOCK["HTTP 400 or 409\nUpload Not Allowed\nin Current State"]
    GUARD -->|"Yes — upload permitted"| RATELIM

    SBLOCK --> START

    subgraph VALIDATE["Validation Layer"]
        direction TB
        RATELIM["Rate Limiter Check\nper-student upload rate\nHTTP 429 on breach"]
        TYPECK["File Type Check\nMust be .zip extension\nHTTP 400 if not ZIP"]
        SIZECK["Compressed Size Check\nAgainst MAX_COMPRESSED_SIZE_MB\nHTTP 413 if exceeded"]
        ZBOMB["ZIP-Bomb Detection\nCumulative decompressed bytes tracked\nAbort if ratio threshold exceeded"]
        PTRAV["Path-Traversal Check\nAll ZIP entries validated before extraction\nReject if entry escapes target dir"]
        CORR["Corrupt ZIP Check\nRaise on invalid or non-ZIP archive"]
        MAL["Malware Scan — Gap\nNot implemented\nNo antivirus integration"]
        VULN["Vulnerability Scan — Gap\nNot implemented\nNo dependency or binary scanner"]
    end

    RATELIM --> TYPECK --> SIZECK --> ZBOMB --> PTRAV --> CORR
    MAL -.->|"Planned — Gap"| CORR
    VULN -.->|"Planned — Gap"| CORR

    CORR -->|"Any validation failure"| REJECT["Upload Rejected\nHTTP 400 or 413\nNo state change on project"]
    REJECT --> START

    CORR -->|"All checks passed"| HASHCK

    HASHCK{"Content hash\nmatch cached\nprior build?"}
    HASHCK -->|"Cache hit — identical ZIP"| CACHED["Serve Prior Compilation\nSkip recompilation\nReuse existing PDF"]
    CACHED --> PERSIST

    HASHCK -->|"New content — proceed"| TFILE

    subgraph COMPILE["Compilation Layer"]
        direction TB
        TFILE[Save ZIP to Temp Workspace\ntask_uuid used as workspace key]
        NEWVER[Create ProjectReportVersion Record\ncompilation_status: idle\nsubmission_status: not_submitted]
        ENQUEUE[Enqueue Celery Task via Redis\nStore task metadata — TTL 2h]
        CELERY[Celery Worker — LaTeX Compile\nExtract ZIP into temp workspace\nRun pdflatex or texlive pipeline]
        SUCCESS[Compile Success\ncompilation_status: success\nPDF + log + artifacts stored in tmp]
        FAILED[Compile Failed\ncompilation_status: failed\nError log preserved]
    end

    TFILE --> NEWVER --> ENQUEUE --> CELERY
    CELERY -->|"Compile succeeded"| SUCCESS
    CELERY -->|"Compile failed"| FAILED

    FAILED --> FAILNOTE["Student Notified via SSE\nFailure reason and log available\nNo attempt consumed\nFree retry"]
    FAILNOTE --> START

    SUCCESS --> PERSIST[Move Artifacts to Temp Workspace\npdf_path · zip_path · log_path set on version]

    subgraph PREVIEW["Student Review Loop — Unlimited Re-runs"]
        direction TB
        PVIEW[Student Views Compiled PDF]
        PEDIT{"Satisfied with\ncompiled output?"}
        PREUP[Edit Source and Re-upload\nNew version created\nPrior compile result replaced]
    end

    PERSIST --> PVIEW
    PVIEW --> PEDIT
    PEDIT -->|"No — needs changes"| PREUP --> START
    PEDIT -->|"Yes — ready to submit"| PRESUB

    PRESUB[Student Submits to Faculty\nPOST to submit endpoint\nRequires compilation_status == SUCCESS]

    PRESUB --> MVFILE[Move Files from Temp to Persistent Storage\npersistent_path: storage_dir/project_id/vN]

    MVFILE --> SUBSTATE["submission_status: submitted\nsubmitted_at timestamp recorded\nStudent edits now locked"]

    SUBSTATE --> DONE(["Report Submitted to Faculty\nProceeds to Faculty Review Workflow"])

    classDef authStyle fill:#0d6efd,stroke:#0a58ca,color:#ffffff
    classDef termStyle fill:#198754,stroke:#157347,color:#ffffff
    classDef failStyle fill:#dc3545,stroke:#b02a37,color:#ffffff
    classDef gapStyle fill:#fd7e14,stroke:#d96a0b,color:#000000
    classDef cacheStyle fill:#6f42c1,stroke:#59359a,color:#ffffff
    classDef compStyle fill:#0a0a2a,stroke:#0d6efd,color:#ffffff
    classDef decStyle fill:#495057,stroke:#343a40,color:#ffffff

    class START authStyle
    class DONE termStyle
    class REJECT,FAILED,FAILNOTE,SBLOCK failStyle
    class MAL,VULN gapStyle
    class CACHED cacheStyle
    class CELERY,ENQUEUE compStyle
    class GUARD,HASHCK,PEDIT decStyle
```

---

## Notes

- **Validation is fully inline**: there is no separate "Security Scanner Service" as described in
  the requirements. All checks (ZIP-bomb, path-traversal, type, size, rate-limit, corrupt-ZIP)
  run within the `UploadService.accept_upload` method and `app/security/zip_validator.py`.
- **Malware and vulnerability scanning are unimplemented** (`Gap`). The system rejects ZIPs that
  are structurally dangerous (bomb/traversal) but does not scan for embedded malicious payloads
  or known CVEs.
- **Content-hash caching**: SHA-256 of the raw ZIP bytes is computed on upload. If the hash
  matches a prior successful compilation for the same project, the existing artifacts are reused
  without re-running the LaTeX compiler.
- **Temp vs. persistent storage**: compiled artifacts first land in a temp workspace keyed by
  `project_id_contentHash`. On student submission, they are copied to
  `PERSISTENT_STORAGE_DIR/project_id/vN`. If the temp directory is missing at submission time,
  the submission still proceeds (paths are null-safe).
- **SSE (Server-Sent Events)**: the student receives real-time compilation progress via a Redis-
  backed SSE stream. Task metadata (keyed `task:{uuid}:meta`) has a 2-hour TTL.
- **Free retries**: compilation failures do **not** decrement `max_tries`. Only faculty
  rejections consume an attempt.

---

## Business Rules

- Upload is only permitted when `submission_status ∈ {NOT_SUBMITTED, REJECTED}` **and**
  `compilation_status ≠ PROCESSING`. Any other combination returns HTTP 400 or 409.
- Only `.zip` files are accepted (type check on file extension). HTTP 400 otherwise.
- File size must be ≤ `MAX_COMPRESSED_SIZE_MB` (checked via `Content-Length` header; streams are
  validated on read). HTTP 413 otherwise.
- Rate limit is enforced per `user_id` (student registration number) via Redis.
- ZIP extraction aborts if the cumulative decompressed size exceeds the configured
  decompression-bomb threshold.
- Every entry in the ZIP is checked for path-traversal (`../`, absolute paths) before extraction.
- `submit_for_review` raises a `ValueError` if `compilation_status ≠ SUCCESS`. Students
  cannot submit a failed or in-progress compile.
- The `SELECT … FOR UPDATE` row lock in `_transition_to_idle` prevents concurrent uploads from
  the same project.

---

## Edge Cases

- **Upload during PROCESSING**: if a Celery task is already running and the student attempts
  another upload, the guard (`compilation_status == PROCESSING → HTTP 409`) blocks it.
- **Enqueue failure after commit**: if Redis is unavailable after the DB commit, the file is
  saved but the task is never dispatched. `rollback_after_enqueue_failure` attempts cleanup but
  cannot undo a committed transaction — the version row persists in an orphaned `idle` state.
- **Temp workspace missing at submission**: `shutil.copytree` is guarded by `tmp_path.exists()`;
  if the temp directory was cleaned up between compile and submit, paths are set to null. The
  submission still proceeds but the stored PDF path is empty.
- **Hash collision (identical ZIP, different content)**: SHA-256 collision probability is
  negligible but non-zero. A collision would serve a cached artifact for the wrong content.
- **Task metadata TTL**: if the student polls the SSE stream more than 2 hours after upload,
  the task metadata has expired and the stream cannot authenticate the request.
