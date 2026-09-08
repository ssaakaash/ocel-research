# ADR-005: Scoring System

- Status: Accepted
- Date: 2026-06-12
- Deciders: Educational Capstone Portal Lead Architecture
- Related:
  - [../architecture/scoring-system.md](../architecture/scoring-system.md)
  - [../architecture/faculty-review.md](../architecture/faculty-review.md)
  - [../diagrams/faculty-review-workflow.md](../diagrams/faculty-review-workflow.md)

## Context

Faculty must record evaluation scores for each report submission. Two schemas coexist during the in-progress migration. The new modular `scores` table is keyed by a unique `(report_version_id, faculty_id)` constraint, while the legacy `scores` table is keyed by a unique `(project_id, version)` constraint. Both store `ai_percentage` and `similarity_percentage` constrained to the `[0,100]` range (nullable in the new schema), plus report file paths (`ai_report_path`, `similarity_report_path`) and a free-text `comment`.

The originally envisioned automated pipeline — OCR extraction of scores and Turnitin-driven similarity reporting — does not exist in code. There is no OCR implementation anywhere (G1, `[Planned]`) and no Turnitin API or parser (G2, `[Planned]`). The current operating reality is that faculty enter scores manually and upload the corresponding report file paths. A scoring entry must be durable and trustworthy once recorded, because it gates the accept/reject decision on a submission.

## Decision

Scores are **write-once and immutable**, keyed per report version per faculty. The write path (`add_project_score` in `app/services/project_service.py`) executes under a `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE` transaction and relies on the database unique constraint to enforce single-write semantics. A second write for the same key is rejected at the application layer with HTTP 400 "Scores are locked". Manual faculty entry is the supported and only score-capture mechanism; OCR/Turnitin automation is explicitly deferred (`[Planned]`).

## Rationale

- A SERIALIZABLE transaction combined with the unique constraint (`(report_version_id, faculty_id)` in the new schema, `(project_id, version)` in the legacy schema) makes the first committed score authoritative and prevents lost-update or write-skew anomalies on a value that drives a downstream accept/reject decision.
- Immutability gives the scoring record audit integrity: once a faculty member commits a score, it cannot be silently altered, which matches the canonical rule that scores are immutable once written and percentages stay within `[0,100]`.
- Versioning by report version (or `(project_id, version)` in legacy) means each resubmission attempt carries its own independent score row, preserving the history implicitly through the version counter rather than through mutation.
- Manual entry is the honest current state: with no OCR (G1) and no Turnitin integration (G2), automated extraction cannot be relied upon, so the system treats the faculty member as the source of truth and stores any AI/similarity report as an uploaded file path alongside the manually typed percentages.

## Consequences

### Positive

- Strong correctness guarantee: concurrent score writes for the same key cannot both succeed, and a recorded score cannot be corrupted after the fact.
- Clear, auditable lineage: each version's score is independent and tied to a specific report version and faculty identity.
- Simple operational model that does not depend on external services (OCR/Turnitin) that are absent.

### Negative / Trade-offs

- The new schema permits null `ai_percentage`/`similarity_percentage`, so a submission can be approved or rejected with no numeric score recorded; a later legitimate numeric score is then blocked by the same unique constraint that enforced immutability (E12).
- Immutability conflicts with any expectation that faculty can correct an extracted or mistyped value. A locked score returns HTTP 400, and — unlike review marks — there is **no edit-request path for scores** (E6).
- There is no `is_editable` flag and no separate edited-value column, so the system cannot capture a before/after correction without violating the write-once rule (G4).
- Two divergent score schemas must be kept consistent during migration, adding drift risk while both remain live.

## Alternatives Considered

- **Mutable scores backed by a history table.** Allow in-place updates while appending each prior value to an audit/history table. Rejected for now: it adds a second write path and a new table, and the absence of `is_editable`/edited-value storage (G4) means the correction-capture machinery does not yet exist. It remains the natural follow-up if score correction becomes a requirement.
- **Automated extraction-first scoring.** Drive scores from OCR (G1) and Turnitin (G2) with faculty merely confirming. Rejected because neither integration exists in code; building the immutable manual-entry path first keeps the system functional and honest about its current capabilities.

## Known Gaps & Follow-ups

- **G1 — OCR Service absent.** Automatic score extraction is unimplemented; scoring is manual entry. `[Planned]`
- **G2 — Turnitin integration absent.** No API or parser; faculty types scores and uploads report file paths. `[Planned]`
- **G4 — No `is_editable` / separate edited-value storage.** Score overwrites are not possible and no before/after correction is captured; reconciling immutability with correction needs (see E6) requires a future edit-request-for-scores mechanism or a history table.
- **E6 — Immutability vs edit requirement.** A locked score (HTTP 400) conflicts with any requirement to edit extracted values; no score edit-request path exists today.
- **E12 — Null scores.** Approve/reject is possible without numeric scores; a null-score row can block a later legitimate numeric score because of the unique constraint.
