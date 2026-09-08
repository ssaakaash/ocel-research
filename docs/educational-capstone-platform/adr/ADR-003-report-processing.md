# ADR-003: Asynchronous Report Processing Pipeline

- Status: Accepted
- Date: 2026-06-12
- Deciders: Educational Capstone Portal Lead Architecture
- Related:
  - [Report Processing architecture](../architecture/report-processing.md)
  - [Report processing pipeline](../diagrams/report-processing-pipeline.md)
  - [Submission sequence](../diagrams/submission-sequence.md)

## Context

Students upload LaTeX source as a ZIP, which the portal must compile to a PDF
using TeX Live / `pdflatex` inside a Docker image
(`docker/Dockerfile.texlive`). Compilation is slow, CPU-bound, and may be
retried repeatedly during a preview loop before submission. Running it inline in
a request handler would block the web worker, hold connections open for the
duration of a compile, and couple request latency to TeX runtime. The pipeline
must validate the upload, compile out-of-band, stream progress back to the user,
and promote artifacts to durable storage only at the moment of submission.

The grounded components are: **Celery** workers
(`app/workers/queue_worker.py`, `pdflatex_worker.py`,
`app/tasks/compile_task.py`); **Redis** for task metadata
(`task:{uuid}:meta`, TTL 7200s) and SSE backing; **Server-Sent Events**
(`app/routers/stream.py`) for real-time compile status; inline ZIP validation
(`app/security/zip_validator.py` + `UploadService`); content-hash caching
(`app/modules/reports/services/cache.py`); and the upload/version logic
(`app/modules/reports/services/upload.py`). Uploads accept `.zip` only, bounded
by `MAX_COMPRESSED_SIZE_MB`, rate-limited per student via Redis, and guarded by
`SELECT … FOR UPDATE` against concurrent upload.

## Decision

Adopt an **asynchronous compile pipeline on Celery + Redis**. The request
handler validates the upload **inline** (ZIP-only, size bound, rate limit, and
the ZIP structural guards), creates a new `ProjectReportVersion` row, and
enqueues a Celery compile task; the worker performs the `pdflatex` compilation
out-of-band and writes task metadata to Redis under `task:{uuid}:meta`
(TTL 7200s).

Use **temporary-to-persistent storage promotion**: compiled output lives in a
temporary workspace during the preview loop and is promoted (copied) to
persistent storage only on `submit_for_review`, which moves tmp → persistent,
locks edits, and sets `submitted_at`.

Reuse prior compilations via **SHA-256 content-hash caching**: the content hash
recorded at `start_compilation` keys the cache so an identical source ZIP reuses
its previous compilation rather than recompiling.

Stream compile progress to the client over **SSE** (`stream.py`), backed by the
Redis task metadata with a **7200-second TTL**.

Validation is **inline**, not a separate service: ZIP-bomb, path-traversal, and
corrupt-ZIP guards run synchronously in `zip_validator.py` via `UploadService`
before the version row is created and the task enqueued.

## Rationale

- Offloading compilation to Celery keeps web workers responsive and decouples
  request latency from TeX runtime, which is essential given repeated preview
  compiles.
- Promoting artifacts to persistent storage only at submit avoids durably
  storing the many throwaway compiles produced during the preview loop, while
  guaranteeing the submitted artifact is durable.
- Content-hash caching makes re-submission of unchanged source cheap and
  deterministic, eliminating redundant `pdflatex` runs.
- SSE over Redis-backed task metadata gives real-time progress without polling
  the database, and the 7200s TTL bounds metadata retention to a single working
  session.
- Inline validation rejects malformed or hostile uploads before any worker or
  storage cost is incurred, keeping the expensive async stage clean.

## Consequences

### Positive

- Web workers stay responsive; compile latency never blocks request handling.
- Throwaway preview compiles never reach persistent storage; only submitted
  artifacts are durable.
- Unchanged source is served from cache, saving compute and producing stable
  output.
- Real-time progress via SSE without database polling.
- Hostile and malformed ZIPs are rejected up front by inline guards.

### Negative / Trade-offs

- The enqueue step is **not transactional** with the version-row commit: if
  enqueue fails after the DB commit, an orphaned `idle` version row remains and
  cannot be rolled back (E8).
- The temp-to-persistent promotion tolerates a missing temp workspace: the
  copy is guarded by an existence check, so paths may be set null and the
  submission still proceeds (E9).
- The SSE/task-metadata TTL (2h) means a stale stream cannot authenticate once
  the metadata expires (E11).
- Inline validation covers only structural threats; there is no malware or
  vulnerability scanning (G3).

## Alternatives Considered

- **Synchronous compile.** Run `pdflatex` inside the request handler and return
  the PDF directly. Rejected: TeX compilation is slow and retried often; inline
  compilation would block web workers, tie up connections, and make request
  latency unpredictable.
- **Object-store-first storage.** Write every compile directly to persistent
  object storage rather than to a temporary workspace promoted on submit.
  Rejected: it would durably persist large volumes of throwaway preview
  compiles and complicate the cache/lifecycle, with no benefit over promoting
  only the submitted artifact.

## Known Gaps & Follow-ups

- **G3 — Malware and vulnerability scanning absent.** Only zip-bomb,
  path-traversal, corrupt-ZIP, size, and type checks exist. Add malware/vuln
  scanning to the upload path. `[Planned]`
- **E8 — Enqueue failure after DB commit.** Define compensation for the orphaned
  `idle` version row (e.g., transactional outbox or reconciliation sweep) since
  `rollback_after_enqueue_failure` cannot undo a committed write.
- **E9 — Temp workspace missing at submit.** The copy is guarded by an existence
  check, so paths can be nulled while the submission proceeds; define whether a
  missing workspace should fail the submission instead.
- **E11 — SSE / task metadata TTL expiry.** Stale streams cannot authenticate
  after the 7200s TTL; define reconnect/refresh behavior for long sessions.
