# Future Roadmap

This document tracks planned and unimplemented capabilities for the Educational Capstone Portal backend. Each item records the current state, target state, dependencies, affected components, and priority, and is tied to the gap ID (`G1`..`G11`) it closes. Items here are not yet in the codebase; they are marked `[Planned]` or `[Future]` and must not be presented as available behavior.

## Purpose

Provide a single, ordered view of work that extends the current system beyond its implemented scope. The roadmap exists to keep planned features traceable to the gaps they resolve and to the source files they will touch, so that onboarding developers can distinguish shipped behavior from intended behavior.

## Scope

In scope: capabilities that are referenced in requirements or diagrams but absent from the codebase, plus reliability improvements to existing subsystems. Out of scope: bug fixes that do not change behavior, and the canonical gap catalog itself (see [known-gaps.md](known-gaps.md) for the authoritative gap and edge-case register).

## Responsibilities

Each roadmap item below is owned as a discrete deliverable. The roadmap is responsible for naming the gap it closes, the components it affects, and the prerequisites that block it. It does not redefine business rules; those remain governed by the implemented state machine and the gap register.

### OCR Integration (G1)

- **Current state:** `[GAP]` No OCR code exists anywhere in the codebase (zero matches). Scoring is manual entry only.
- **Target state:** `[Planned]` An OCR Service that extracts scores automatically from uploaded review documents and pre-fills score fields for faculty confirmation.
- **Dependencies:** A scoring model that can capture machine-extracted values distinctly from faculty-entered values — blocked by `G4` (no `is_editable`, no separate edited-value storage). Closing `G4` is a prerequisite so extracted values can be reviewed and corrected without violating score immutability (`E6`).
- **Affected components:** `app/services/project_service.py` (`add_project_score`, SERIALIZABLE lock), the new modular `scores` model under `app/modules/reports/`, and the faculty review entry points in `app/routers/faculty.py`.
- **Priority:** Medium. Improves throughput of an already-functional manual flow; not a correctness blocker.

### Turnitin Integration (G2)

- **Current state:** `[GAP]` No Turnitin API client or report parser. Faculty type similarity/AI scores manually and upload report file paths (`ai_report_path`, `similarity_report_path`).
- **Target state:** `[Planned]` A Turnitin Service that submits artifacts, retrieves similarity and AI percentages, and populates `similarity_percentage` / `ai_percentage` automatically.
- **Dependencies:** Same scoring-model prerequisite as OCR (`G4`); the immutability conflict (`E6`) must be resolved so automated values can be revised before the score is locked.
- **Affected components:** `app/services/project_service.py`, the modular `scores` model, artifact storage paths managed via `project_report_artifacts`, and `app/routers/faculty.py`.
- **Priority:** Medium. Removes manual percentage entry and the associated transcription risk.

### Malware Scanning (G3)

- **Current state:** `[GAP]` Inline validation covers ZIP-bomb, path-traversal, corrupt-ZIP, type, and size only. There is no malware scanner; the "Security Scanner Service" is not a service.
- **Target state:** `[Planned]` Malware scanning of uploaded ZIP contents before extraction/compilation, integrated into the upload validation path.
- **Dependencies:** An out-of-process scanning engine or sidecar; integration point in the upload pipeline that can quarantine and reject without breaking the rate-limited, row-locked upload guard.
- **Affected components:** `app/security/zip_validator.py`, `app/modules/reports/services/upload.py`, and `app/security/rate_limiter.py`.
- **Priority:** High. Uploaded archives are compiled in a TeX Live container; unscanned content is a direct security exposure.

### Vulnerability Scanning (G3)

- **Current state:** `[GAP]` No vulnerability scanning of submitted source archives; covered by the same gap as malware scanning (`G3`).
- **Target state:** `[Future]` Static analysis / vulnerability scanning of extracted source trees prior to compilation, with findings surfaced to faculty and admins.
- **Dependencies:** Malware scanning integration (above) should land first to establish the quarantine and reject path; shares the same upload-pipeline hook.
- **Affected components:** `app/security/zip_validator.py`, `app/modules/reports/services/upload.py`, and `app/modules/reports/services/compile.py` (compilation, 37KB).
- **Priority:** Medium. Hardening on top of malware scanning rather than a standalone correctness requirement.

### Review Automation (G5)

- **Current state:** `[GAP]` Stage advancement `R1 → R2 → R3` is not wired. `ensure_project_report` always defaults `review_milestone='R1'`; `state.py` never advances the milestone, and `max_tries` is not reset per stage. Coordinator marks management exists but is not driven by submission-machine transitions.
- **Target state:** `[Future]` Automated stage advancement on acceptance, per-stage `max_tries` reset, and automation linking coordinator mark entry/confirmation to the submission lifecycle.
- **Dependencies:** Resolving the dead `REJECTED` state and attempts handling (`G7`, `G9`) so stage transitions are deterministic; consistency across the dual data models (`G6`) so advancement is not lost to write skew (`E15`).
- **Affected components:** `app/modules/reports/services/state.py`, the report header `project_reports.review_milestone`, and `app/modules/project_coordinator/` (review events/panels/marks).
- **Priority:** High. Without it, the three-stage workflow described by the requirements is not actually enforced end-to-end.

### Notification Improvements (G11)

- **Current state:** Implemented but fragile. The in-process event bus (`app/shared/events`) and notification writer (`app/shared/notifications/writer.py`) function, but handlers can swallow failures: the `ProjectConfirmed` capacity handler logs a warning and confirms anyway on a decrement `ValueError` (`E5`), so downstream notification/side-effect reliability is not guaranteed. These subsystems are part of the out-of-prose set tracked under `G11`.
- **Target state:** `[Future]` Durable, retry-capable notification delivery with explicit failure handling instead of swallowed exceptions, and observability over dropped events.
- **Dependencies:** A decision on in-process vs. durable queueing; alignment with the audit trail so dropped notifications are recorded rather than silently lost.
- **Affected components:** `app/shared/events/`, `app/shared/notifications/writer.py`, `app/routers/notifications.py`, and the `ProjectConfirmed` handler in `app/modules/project_registration/events.py`.
- **Priority:** Medium. Existing flows work, but silent failure (`E5`) undermines trust in delivery guarantees.

## Workflow References

- [Faculty review workflow](../diagrams/faculty-review-workflow.md) — review, manual scoring, and the `[Planned]` OCR/Turnitin steps (`G1`, `G2`).
- [Report processing pipeline](../diagrams/report-processing-pipeline.md) — upload, validation, and compile path that malware/vulnerability scanning (`G3`) extends.
- [Submission stage workflow](../diagrams/submission-stage-workflow.md) — the `R1/R2/R3` stages whose automation is gated by `G5`.
- Authoritative gap and edge-case catalog: [known-gaps.md](known-gaps.md).

## Business Rules

The roadmap does not introduce new business rules. Planned features must preserve existing invariants: scores remain immutable once written (`[0,100]` or NULL; unique `(report_version_id, faculty_id)`); uploads remain `.zip`-only, size-bounded, rate-limited, and row-locked; compile failures stay free of `max_tries` decrement; and every state transition continues to write an `AuditLog` row. Any automation (OCR, Turnitin, stage advancement) must operate within these rules or first close the gap that relaxes them (notably `G4` for editable extracted values).

## Constraints

- New integrations (`G1`, `G2`, `G3`) introduce external dependencies and must not block or slow the synchronous upload/compile path beyond its current rate-limited budget.
- Stage automation (`G5`) must be consistent across both data-model layers while the migration (`G6`) is in progress; cross-model write skew (`E15`) is a live hazard.
- Notification durability (`G11`) is constrained by the current in-process event bus design; durable delivery may require infrastructure not present today.

## Edge Cases

Planned work must explicitly address the edge cases it touches:

- `E5` — capacity-overrun handler swallows the decrement `ValueError`; Notification Improvements must surface rather than hide such failures.
- `E6` — locked-score immutability conflicts with editing extracted values; OCR (`G1`) and Turnitin (`G2`) automation depend on resolving this via `G4`.
- `E12` — null score values are accepted under the new schema; automated scoring must not let a null write block a later legitimate score.
- `E15` — cross-model write skew during migration; stage automation (`G5`) must not lose advancement state across the legacy/modular split.

## Security Considerations

Malware and vulnerability scanning (`G3`) are the security-critical roadmap items: uploaded archives are extracted and compiled inside a TeX Live Docker container, and today only structural ZIP guards apply. Until `G3` lands, the container boundary and inline validation in `app/security/zip_validator.py` remain the only defenses. External integrations (`G1`, `G2`) introduce new outbound trust boundaries and credential-handling requirements that must respect the existing security headers and OAuth/JWT model.

## Implementation Notes

- Scoring automation touches `app/services/project_service.py` (`add_project_score`, SERIALIZABLE lock) and the modular `scores` model under `app/modules/reports/`.
- Scanning hooks belong in `app/modules/reports/services/upload.py` and `app/security/zip_validator.py`, alongside `app/security/rate_limiter.py`.
- Stage advancement is centered on `app/modules/reports/services/state.py` and the `project_reports.review_milestone` header, coordinated with `app/modules/project_coordinator/`.
- Notification reliability work targets `app/shared/events/`, `app/shared/notifications/writer.py`, and `app/modules/project_registration/events.py`.

## Future Enhancements

Beyond the items above, the out-of-prose subsystems catalogued under `G11` (venue booking and multi-step approvals, re-review applications, absentee permissions, guide reassignment and capacity, visibility locks, programme/course/academic-term structure, and outcome/accreditation artifacts) are candidates for first-class documentation and requirement coverage. These are `[Future]` documentation and hardening targets rather than new features. The canonical list of gaps and their remediation lives in [known-gaps.md](known-gaps.md).
