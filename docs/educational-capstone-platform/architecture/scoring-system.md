# Scoring System

The scoring system records the AI-similarity and plagiarism-similarity percentages a faculty member assigns to a report version. Scores are entered manually, persisted as immutable versioned records, and written under a SERIALIZABLE transaction that locks the score against later overwrite.

## Purpose

Define how scores are captured, stored, and protected against mutation, and to record the planned automated-extraction features (OCR, Turnitin) that are not yet implemented.

## Scope

Covers the score data models (legacy and new), the immutability and locking guarantees, manual score entry via `add_project_score`, and the planned integrations. The faculty decision flow that surrounds scoring is covered in [faculty-review.md](faculty-review.md).

### Current State (manual entry)

Scoring is entirely manual. Faculty type the AI and similarity percentages and upload report file paths (`ai_report_path`, `similarity_report_path`). There is no automated extraction. `app/services/project_service.py:add_project_score` writes the score under `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE`; a second write for the same version returns HTTP 400 "Scores are locked".

### Future OCR Integration

Automatic extraction of scores via OCR is unimplemented `[GAP]` (G1). There is no OCR code anywhere in the codebase; the "OCR extracts scores automatically" requirement is `[Planned]`.

### Future Turnitin Integration

Turnitin integration is unimplemented `[GAP]` (G2). There is no API client or report parser; faculty enter scores manually and upload report file paths. This is `[Planned]`.

### Score Locking

A score is locked once written. The new `scores` table enforces `unique (report_version_id, faculty_id)`; the legacy `scores` table enforces `unique (project_id, version)`. Combined with the SERIALIZABLE write, the unique constraint makes the first write authoritative and rejects any second write with HTTP 400.

### Manual Overrides

There is no in-place override mechanism `[GAP]` (G4). The schema has no `is_editable` flag and no separate edited-value column, so there is no before/after capture and no score-correction-specific audit fields. Editing an extracted value would require overwriting a locked record, which the lock forbids (E6). This capability is `[Planned]`.

### Audit Requirements

Score writes occur within the audited transition flow, but the schema lacks dedicated score-correction audit fields (no before/after values) `[GAP]` (G4). General transition auditing is covered by the audit subsystem; score-specific correction history is `[Planned]`.

## Responsibilities

- Persist a single immutable score per `(report_version_id, faculty_id)` (new) / `(project_id, version)` (legacy).
- Enforce immutability via the unique constraint and SERIALIZABLE write.
- Reject overwrite attempts with HTTP 400 "Scores are locked".
- Validate that percentage values fall within `[0, 100]`.

## Workflow References

- [../diagrams/faculty-review-workflow.md](../diagrams/faculty-review-workflow.md) — review, Turnitin upload, manual scoring, OCR/Turnitin [Planned], decision.
- Related docs: [faculty-review.md](faculty-review.md), [audit-trail.md](audit-trail.md).

## Business Rules

- One score per `(report_version_id, faculty_id)` (new schema); legacy: one per `(project_id, version)`.
- A score is immutable once written (unique constraint + SERIALIZABLE transaction).
- A second write for the same key returns HTTP 400 "Scores are locked".
- Percentage values must lie in `[0, 100]`.
- In the new schema, `ai_percentage` and `similarity_percentage` may be NULL.

## Constraints

- Two model layers coexist: the new `scores` (`ai_percentage`/`similarity_percentage` nullable, `[0,100]` or NULL; `ai_report_path`, `similarity_report_path`, `comment`) and the legacy `scores` (`[0,100]` plus `flag`).
- Writes require the SERIALIZABLE isolation level, so concurrent writers to the same key serialize and the loser is rejected.
- The new schema permits NULL percentages, which can be persisted before numeric values are known (E12).

## Edge Cases

- **E6** — Score immutability versus "faculty may edit values": a locked score (HTTP 400) conflicts with the requirement to edit extracted values; unlike review marks, there is no edit-request path for scores.
- **E12** — Null score values accepted (new schema): approve/reject is possible without numeric scores, and a NULL-valued row can block a later legitimate score via the unique constraint.

## Security Considerations

Score writes are restricted to the guide role and serialized under SERIALIZABLE isolation, preventing concurrent tampering and double-writes. Because there is no edit path and no edited-value capture (G4), there is also no audit record of correction attempts; this limits forensic visibility into disputed scores. Authorization and transport protections are described in [security-model.md](security-model.md).

## Implementation Notes

- `app/services/project_service.py` — `add_project_score`, the SERIALIZABLE versioned write and HTTP 400 lock.
- `app/models/*` — legacy `Score` model (`unique (project_id, version)`, `flag`).
- `app/modules/reports/models/*` — new `scores` model (`unique (report_version_id, faculty_id)`, nullable percentages, report paths, comment).
- `app/services/admin_service.py` — administrative score management.

## Future Enhancements

- **G1** — OCR Service to extract scores automatically from uploaded reports. Currently absent; `[Planned]`.
- **G2** — Turnitin integration (API client and report parser) to replace manual entry of similarity scores. Currently absent; `[Planned]`.
- **G4** — Add `is_editable` and separate edited-value storage with before/after capture and score-correction audit fields, enabling controlled manual overrides without violating immutability. Currently absent; `[Planned]`.
