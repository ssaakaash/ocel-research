# Report Processing

The report processing subsystem accepts a student-uploaded ZIP archive, validates it inline, compiles its LaTeX sources to a PDF through asynchronous Celery workers, and produces the artifacts attached to a report version. It is the asynchronous heart of the submission workflow, mediating between the upload entry point, the compilation workers, and the submission state machine.

## Purpose

Provide a safe, idempotent, and observable pipeline that turns an uploaded source archive into a compiled PDF and associated artifacts, while protecting the platform from hostile or malformed uploads and avoiding redundant compilation work.

## Scope

Covers the path from `accept_upload` through validation, compilation, artifact persistence, and the preview loop up to (but not including) `submit_for_review`. It includes upload acceptance, ZIP validation, the Celery-based compilation pipeline, artifact generation, content-hash caching, version creation, retry handling, and the concurrency controls that serialize work per submission. Faculty review and scoring are out of scope (see [faculty-review.md](faculty-review.md) and [scoring-system.md](scoring-system.md)).

### ZIP Validation

Uploads are validated inline by `app/security/zip_validator.py` together with `UploadService`. Accepted archives must be `.zip` only and within `MAX_COMPRESSED_SIZE_MB`. The validator guards against decompression bombs, path traversal during extraction, and corrupt ZIP structures. No malware or vulnerability scanning is performed `[GAP]` (G3).

### Compilation Pipeline

`app/modules/reports/services/compile.py` drives compilation. `start_compilation` transitions the submission to `PROCESSING` and records the SHA-256 `content_hash`. Compilation runs on Celery workers (`app/workers/queue_worker.py`, `pdflatex_worker.py`, `app/tasks/compile_task.py`) using TeX Live / pdflatex inside the `docker/Dockerfile.texlive` image. Status is streamed to clients over SSE (`app/routers/stream.py`). On completion, `compilation_success` moves the submission to `SUCCESS`; `compilation_failed` moves it to `FAILED` and permits a free retry.

### Artifact Generation

A successful compilation produces a `project_report_versions` row whose `pdf_path` is the compiled report and whose `zip_path` is the uploaded source. Additional artifacts are persisted in `project_report_artifacts`, keyed `unique (report_version_id, artifact_type)` over `ppt | poster | sdg_plan | outcome_plan | outcome_status | outcome_attainment_proof`. There is no `source_code` or `final_report` artifact type: source is the version `zip_path` and the report is the version `pdf_path`.

### Caching

`app/modules/reports/services/cache.py` implements content-hash (SHA-256) caching. When an upload's `content_hash` matches a prior compilation, the cached result is reused instead of recompiling, avoiding redundant worker load.

### Versioning

Each accepted upload creates a new `ProjectReportVersion` and resets compilation state to `IDLE`. The submission `version` counter is monotonic; a faculty rejection later increments it (see [faculty-review.md](faculty-review.md)). Report versions are uniquely keyed `(report_id, version)` with `version >= 1`.

### Retry Logic

Compilation failures are free: `compilation_failed` transitions to `FAILED` without consuming an attempt, and the student may recompile. Only faculty rejections consume `max_tries`. This separation keeps build flakiness from depleting a student's three review attempts per stage.

### Concurrency Controls

Upload acceptance takes a `SELECT … FOR UPDATE` row lock on the submission to serialize concurrent uploads. A per-student Redis rate limit (`app/security/rate_limiter.py`) throttles upload frequency. If the submission is already `PROCESSING`, a new upload is rejected with HTTP 409 (E7).

## Responsibilities

- Accept and validate uploads (`.zip` only, size, rate limit, structural guards).
- Create a new report version per accepted upload and reset compilation state.
- Enqueue and track compilation on Celery workers; stream status over SSE.
- Persist the compiled PDF, source ZIP, and accreditation artifacts.
- Reuse prior compilations via content-hash caching.
- Serialize concurrent work per submission via row locking and the 409 guard.

## Workflow References

- [../diagrams/report-processing-pipeline.md](../diagrams/report-processing-pipeline.md) — upload → validation → compile → preview loop → submit.
- [../diagrams/submission-sequence.md](../diagrams/submission-sequence.md) — upload→compile→review→decision message flow.
- Related docs: [submission-state-machine diagram](../diagrams/submission-state-machine.md), [security-model.md](security-model.md), [faculty-review.md](faculty-review.md).

## Business Rules

- Uploads must be `.zip` only and `<= MAX_COMPRESSED_SIZE_MB`.
- A per-student Redis rate limit applies to uploads.
- Extraction is guarded against decompression bombs, path traversal, and corrupt ZIPs.
- Upload acceptance requires `submission_status ∈ {NOT_SUBMITTED, REJECTED}` and `compilation_status ≠ PROCESSING`.
- A `SELECT … FOR UPDATE` row lock prevents concurrent uploads to the same submission.
- An upload attempted while the submission is `PROCESSING` returns HTTP 409.
- Identical content (SHA-256 `content_hash`) reuses the cached compilation.
- Compile failures are free retries; they do not decrement `max_tries`.

## Constraints

- Compilation runs in a temporary workspace; `submit_for_review` copies temporary outputs to persistent storage. The copy is guarded by an existence check, so a missing temp workspace leaves paths null and lets submission proceed (E9).
- Task metadata and SSE backing live in Redis under `task:{uuid}:meta` with a TTL of 7200s (2 hours); stale polling cannot authenticate after expiry (E11).
- Compilation depends on the TeX Live / pdflatex Docker image and available Celery worker capacity.

## Edge Cases

- **E7** — Concurrent upload during `PROCESSING` is blocked by the `FOR UPDATE` lock and the HTTP 409 guard.
- **E8** — Enqueue failure after the DB commit leaves an orphaned `idle` version row; `rollback_after_enqueue_failure` cannot undo the committed write.
- **E9** — Missing temp workspace at submit: the `copytree` is guarded by `exists()`, paths are set null, and submission proceeds.
- **E11** — SSE / task metadata TTL (2h) expiry: the stream cannot authenticate stale polling.

## Security Considerations

Input validation is the primary defense: `.zip`-only typing, size limits, rate limiting, and structural guards against bombs, traversal, and corruption. These mechanisms are detailed in [security-model.md](security-model.md). There is no malware or vulnerability scanning of uploaded content `[GAP]` (G3); a malicious payload that passes the structural guards is not detected. Task metadata expiry (E11) also bounds the window in which a streaming session remains authenticated.

## Implementation Notes

- `app/modules/reports/services/upload.py` — upload validation and version creation.
- `app/modules/reports/services/compile.py` — compilation orchestration (large module, ~37KB).
- `app/modules/reports/services/cache.py` — content-hash caching.
- `app/security/zip_validator.py` — bomb, traversal, and corrupt-ZIP guards.
- `app/security/rate_limiter.py` — Redis-backed per-student rate limit.
- `app/modules/reports/services/state.py` — submission state machine (`start_compilation`, `compilation_success`, `compilation_failed`).
- `app/workers/queue_worker.py`, `app/workers/pdflatex_worker.py`, `app/tasks/compile_task.py` — Celery workers.
- `app/routers/stream.py` — SSE status streaming.

## Future Enhancements

- **G3** — Add malware and vulnerability scanning of uploaded archives. The current pipeline only enforces zip-bomb, path-traversal, corrupt-ZIP, size, and type checks; content-level threat detection is `[Planned]`.
