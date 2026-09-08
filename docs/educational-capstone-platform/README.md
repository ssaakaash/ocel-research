# Educational Capstone Portal Documentation

Educational Capstone Portal is the Capstone Project Management Portal backend: an asynchronous FastAPI application that manages the full lifecycle of capstone projects, from idea or proposal registration through team formation, report compilation, multi-stage submission, faculty review, and scoring. This directory is the canonical documentation set for developers onboarding to the system; it pairs prose architecture documents and architecture decision records (ADRs) with rendered Mermaid diagrams.

## Project Overview

Educational Capstone Portal coordinates capstone projects between students, faculty (in several roles), and administrators. Students register ideas and form teams, or faculty publish proposals; either path converges on a created project. Teams then upload LaTeX report sources, compile them asynchronously into PDFs, submit across three review stages, and receive faculty review decisions and scores.

Tech stack (facts §0):

- **FastAPI** (async) with **Pydantic** schemas for routers and request/response models.
- **SQLAlchemy async** ORM with **Alembic** migrations, backed by **PostgreSQL** (`postgresql.UUID`, `SERIALIZABLE` isolation, server defaults).
- **Celery** workers for LaTeX compilation, with **Redis** for rate limiting, task metadata (`task:{uuid}:meta`, TTL 7200s), and SSE backing.
- **Server-Sent Events (SSE)** for real-time compile status.
- **TeX Live / pdflatex** compilation inside a Docker image, fronted by a **Caddy** reverse proxy.
- An in-process **event bus** plus a **notification writer** for asynchronous side effects.

**Two-model migration note ([GAP] G6):** two model layers currently coexist. The **legacy** layer (`app/models/*`) still backs the live submission state machine (`app/modules/reports/services/state.py` writes the legacy `Project`). The **new modular** layer (`app/modules/{project_registration,project_coordinator,reports,venue_booking}/models/*`) is the post-migration target, with modules exposing stable interfaces through `contracts.py`. This divergence is the dominant source of drift risk during migration and is referenced throughout these docs as G6.

## Architecture Overview

The portal is organized around a small set of principal actors, a dual-path registration flow that converges on a single project entity, an asynchronous compile-and-submit pipeline, and a faculty review/scoring loop. Every state transition is audited. For the full picture, see [architecture/system-overview.md](architecture/system-overview.md); for the end-to-end visual, see the executive overview diagram, [diagrams/executive-overview.md](diagrams/executive-overview.md).

## System Actors

Principal (authenticated) actors:

- **Student** — creates ideas, forms teams, uploads/compiles/submits reports.
- **Team Leader** — a role value (`student_project.role='leader'`), not a separate identity; only the leader may submit the idea.
- **Faculty** — holds one or more faculty roles below.
- **Admin** — approves faculty proposals, performs user CRUD and CSV bulk upload, sets visibility locks.

Faculty roles (`faculty_roles.role_type`):

- **Guide** — approves/rejects ideas; opens/reviews submissions; accepts/rejects submissions; records scores.
- **Project Coordinator** — schedules review events and panels; manages marks; approves mark edit-requests.
- **Panel Member** — enters review marks.
- **HOD** — approves/rejects re-review applications; approves mark edit-requests; venue approval role.
- **Dean** — venue approval role; broader academic authority [INFERENCE].

Service / system actors:

- **Report Processing Service** (Celery worker), **Notification service / event bus**, **Audit logger**, and **Redis**.
- **Security Scanner Service** is inline validation only, not a standalone service; malware/vulnerability scanning is [GAP] G3.
- **OCR Service** ([GAP] G1) and **Turnitin Service** ([GAP] G2) are [Planned] and absent.

See [architecture/actors-and-roles.md](architecture/actors-and-roles.md) for the full permissions matrix and approval powers.

## Major Workflows

- **Student registration** — idea → team → member confirmation → guide approve/reject → restart. See [architecture/project-registration.md](architecture/project-registration.md) and [diagrams/student-registration.md](diagrams/student-registration.md).
- **Faculty registration** — proposal → admin approve/reject. See [architecture/project-registration.md](architecture/project-registration.md) and [diagrams/faculty-registration.md](diagrams/faculty-registration.md).
- **Report processing** — upload → validation → compile → preview loop → submit. See [architecture/report-processing.md](architecture/report-processing.md) and [diagrams/report-processing-pipeline.md](diagrams/report-processing-pipeline.md).
- **Submission stages** — the three review stages (R1/R2/R3), attempts, and terminal failure. See [architecture/submission-system.md](architecture/submission-system.md) and [diagrams/submission-stage-workflow.md](diagrams/submission-stage-workflow.md).
- **Faculty review** — review, report upload, manual scoring, decision (with OCR/Turnitin [Planned]). See [architecture/faculty-review.md](architecture/faculty-review.md) and [diagrams/faculty-review-workflow.md](diagrams/faculty-review-workflow.md).
- **Scoring** — versioned, immutable scores written under a SERIALIZABLE lock. See [architecture/scoring-system.md](architecture/scoring-system.md) and [diagrams/submission-sequence.md](diagrams/submission-sequence.md).

## State Machines

The system is governed by three primary machines plus a scoring lifecycle:

- **Project lifecycle** — idea/proposal through R1/R2/R3 to locked. See [diagrams/project-lifecycle-state-machine.md](diagrams/project-lifecycle-state-machine.md).
- **Submission** — the dual-axis `compilation_status` × `submission_status` machine. See [diagrams/submission-state-machine.md](diagrams/submission-state-machine.md).
- **Review** — review marks (`draft → confirmed → locked`) and the edit-request path.
- **Scoring lifecycle** — scores are written once and locked (immutable; second write rejected).

Full transition tables and guards are in [architecture/state-machines.md](architecture/state-machines.md).

## Documentation Structure

Master index of every document in this directory (1 README + 13 architecture + 7 ADR + 11 diagrams = 32).

| File | Description |
|---|---|
| [README.md](README.md) | This master index and onboarding entry point. |
| [architecture/system-overview.md](architecture/system-overview.md) | End-to-end system context: actor journeys, registration convergence, compile/submit/finalize flow. |
| [architecture/actors-and-roles.md](architecture/actors-and-roles.md) | Every actor, responsibilities, permissions matrix, and approval powers. |
| [architecture/domain-model.md](architecture/domain-model.md) | Core entities, relationships, and cardinality; legacy vs modular models. |
| [architecture/project-registration.md](architecture/project-registration.md) | Dual registration paths (student idea and faculty proposal) and convert-to-project. |
| [architecture/submission-system.md](architecture/submission-system.md) | Three-stage submission, attempts, accept/reject loop, terminal states. |
| [architecture/report-processing.md](architecture/report-processing.md) | Upload, validation, Celery/Redis async compile, caching, SSE. |
| [architecture/faculty-review.md](architecture/faculty-review.md) | Faculty review, report upload, manual scoring, and decision flow. |
| [architecture/scoring-system.md](architecture/scoring-system.md) | Versioned immutable scores, SERIALIZABLE locking, manual entry. |
| [architecture/audit-trail.md](architecture/audit-trail.md) | AuditLog on every transition, system actors, observability. |
| [architecture/security-model.md](architecture/security-model.md) | OAuth/JWT, inline ZIP guards, rate limiting, security headers. |
| [architecture/state-machines.md](architecture/state-machines.md) | All state vocabularies, transitions, and guards in one place. |
| [architecture/future-roadmap.md](architecture/future-roadmap.md) | Planned features and migration completion roadmap. |
| [architecture/known-gaps.md](architecture/known-gaps.md) | Catalogued gaps (G1..G11) and edge cases (E1..E15). |
| [adr/ADR-001-project-registration.md](adr/ADR-001-project-registration.md) | Decision: dual initiation and convert-to-project (`registration_source`). |
| [adr/ADR-002-team-locking.md](adr/ADR-002-team-locking.md) | Decision: leader-only submit, membership PK, confirmation handshake, lock-on-submit. |
| [adr/ADR-003-report-processing.md](adr/ADR-003-report-processing.md) | Decision: Celery+Redis async compile, tmp→persistent, content-hash cache, SSE. |
| [adr/ADR-004-submission-state-machine.md](adr/ADR-004-submission-state-machine.md) | Decision: dual-axis status machine, guards, max_tries, reject loop. |
| [adr/ADR-005-scoring-system.md](adr/ADR-005-scoring-system.md) | Decision: versioned immutable scores, SERIALIZABLE lock, manual entry. |
| [adr/ADR-006-audit-trail.md](adr/ADR-006-audit-trail.md) | Decision: AuditLog on every transition with system actors. |
| [adr/ADR-007-security-validation.md](adr/ADR-007-security-validation.md) | Decision: inline ZIP guards, rate limit, OAuth/JWT, security headers. |
| [diagrams/executive-overview.md](diagrams/executive-overview.md) | End-to-end lifecycle across both registration paths to finalization. |
| [diagrams/student-registration.md](diagrams/student-registration.md) | Student idea → team → confirm → guide approve/reject → restart. |
| [diagrams/faculty-registration.md](diagrams/faculty-registration.md) | Faculty proposal → admin approve/reject. |
| [diagrams/report-processing-pipeline.md](diagrams/report-processing-pipeline.md) | Upload → validation → compile → preview loop → submit. |
| [diagrams/submission-stage-workflow.md](diagrams/submission-stage-workflow.md) | R1/R2/R3 stages, attempts, terminal failure. |
| [diagrams/faculty-review-workflow.md](diagrams/faculty-review-workflow.md) | Review, report upload, manual scoring, decision (OCR/Turnitin [Planned]). |
| [diagrams/project-lifecycle-state-machine.md](diagrams/project-lifecycle-state-machine.md) | Full project lifecycle (idea/proposal → R1/R2/R3 → locked). |
| [diagrams/submission-state-machine.md](diagrams/submission-state-machine.md) | Dual-axis compilation × submission status machine. |
| [diagrams/submission-sequence.md](diagrams/submission-sequence.md) | Upload→compile→review→decision message flow. |
| [diagrams/enterprise-swimlane.md](diagrams/enterprise-swimlane.md) | Actor lanes: Student/Faculty/Admin/Portal/Processing. |
| [diagrams/domain-model.md](diagrams/domain-model.md) | Core entities and cardinality (ER diagram). |

## Diagram Index

All diagrams are rendered Mermaid under `diagrams/`. Reference them; do not duplicate their source.

| Diagram | Type | Shows |
|---|---|---|
| [diagrams/executive-overview.md](diagrams/executive-overview.md) | flowchart TD | End-to-end lifecycle, both registration paths, processing, finalization. |
| [diagrams/student-registration.md](diagrams/student-registration.md) | flowchart TD | Student idea → team → confirm → guide approve/reject → restart. |
| [diagrams/faculty-registration.md](diagrams/faculty-registration.md) | flowchart TD | Faculty proposal → admin approve/reject. |
| [diagrams/report-processing-pipeline.md](diagrams/report-processing-pipeline.md) | flowchart TD | Upload → validation → compile → preview loop → submit. |
| [diagrams/submission-stage-workflow.md](diagrams/submission-stage-workflow.md) | flowchart TD | R1/R2/R3 stages, attempts, terminal failure. |
| [diagrams/faculty-review-workflow.md](diagrams/faculty-review-workflow.md) | flowchart TD | Review, Turnitin upload, manual scoring, OCR/Turnitin [Planned], decision. |
| [diagrams/project-lifecycle-state-machine.md](diagrams/project-lifecycle-state-machine.md) | stateDiagram-v2 | Full project lifecycle (idea/proposal → R1/R2/R3 → locked). |
| [diagrams/submission-state-machine.md](diagrams/submission-state-machine.md) | stateDiagram-v2 | Dual-axis compilation × submission status machine. |
| [diagrams/submission-sequence.md](diagrams/submission-sequence.md) | sequenceDiagram | Upload→compile→review→decision message flow (autonumbered). |
| [diagrams/enterprise-swimlane.md](diagrams/enterprise-swimlane.md) | flowchart LR | Actor lanes: Student/Faculty/Admin/Portal/Processing. |
| [diagrams/domain-model.md](diagrams/domain-model.md) | erDiagram | Core entities and cardinality. |

## Developer Onboarding Path

Recommended reading order for a new engineer:

1. **[README.md](README.md)** — this index; understand the documentation layout and tech stack.
2. **[architecture/system-overview.md](architecture/system-overview.md)** — the end-to-end system context and actor journeys.
3. **[architecture/actors-and-roles.md](architecture/actors-and-roles.md)** — who can do what (permissions matrix, approval powers).
4. **[architecture/domain-model.md](architecture/domain-model.md)** — the core entities and the legacy/modular split (G6).
5. **[architecture/submission-system.md](architecture/submission-system.md)** and **[architecture/state-machines.md](architecture/state-machines.md)** — the three-stage submission flow and all transition guards.
6. **[architecture/report-processing.md](architecture/report-processing.md)** — the async compile pipeline (Celery/Redis/SSE).
7. **[architecture/faculty-review.md](architecture/faculty-review.md)** and **[architecture/scoring-system.md](architecture/scoring-system.md)** — review decisions and immutable scoring.
8. **[architecture/security-model.md](architecture/security-model.md)** — authentication, upload guards, and security headers.
9. **[architecture/known-gaps.md](architecture/known-gaps.md)** — gaps (G1..G11) and edge cases (E1..E15) before changing anything.
10. **[adr/ADR-001-project-registration.md](adr/ADR-001-project-registration.md)** through **[adr/ADR-007-security-validation.md](adr/ADR-007-security-validation.md)** — the decisions behind each subsystem.
