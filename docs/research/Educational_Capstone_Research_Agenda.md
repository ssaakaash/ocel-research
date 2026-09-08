# Educational Capstone Portal Research Agenda
### Educational Capstone Portal as a Process-Aware Academic Knowledge Graph — a multi-paper research programme
**Core framing (revised after reviewer feedback):** Educational Capstone Portal is **not** "an academic repository with LLM features." It is a **Process-Aware Academic Knowledge Graph / Digital Twin** that instruments the *complete lifecycle* of university research artifacts — registration, supervision, collaboration, submission, evaluation, and software evolution — at the **database/event level**. The publishable novelty lives in that process/provenance substrate (temporal knowledge graphs, object-centric process mining, digital twins, provenance-grounded intelligence), which is far harder to replicate than "LLM over university PDFs."
**Prepared as the foundation for a multi-paper research programme (IEEE / ACM / Springer / Elsevier).**
Date: 2026-07-22 · Grounded in the Educational Capstone Portal architecture docs + graphify knowledge graph (`graphify-out/`, 182 nodes / 366 edges / 14 communities).

> **Verification status (updated 2026-07-22).** Citations were originally drafted from the author-model's training knowledge (cutoff Jan 2026) and have now been **verified via live literature search (Exa)**. Foundational citations checked out (SciNCL — Ostendorff, EMNLP 2022; SPECTER2/SciRepEval — Singh et al., EMNLP 2023; HippoRAG — Gutiérrez, NeurIPS 2024; Self-RAG — Asai, ICLR 2024; GraphRAG — Edge et al., arXiv:2404.16130). **The search also surfaced 2024–2026 prior art that materially reduces several novelty claims (R2, R3, R5, R7, R9) and revealed a close prior system (DevProjAnalytics).** See the new **§4.5 Prior-Art Reality Check** for the honest re-positioning; affected ideas in §7 carry an inline ⚠ note. Anything the graphify graph could not ground is marked **[ASSUMPTION]**.

> **Team 1 update (2026-09-08).** Miri et al. (2026) already demonstrate object-centric educational process mining and Moodle-to-OCEL extraction. Any older statement below that claims a first educational use or the absence of educational prior work is superseded by `Team1_Literature_Review.docx`. Team 1 now positions its contribution around the transactional capstone lifecycle, documentation-grounded validation, Cross-Object Observability Coverage, and a reproducible synthetic benchmark. Generalizable claims require real-log validation.

---

## 1. Executive Summary

Educational Capstone Portal today is a **process-aware capstone-project management backend** (async FastAPI + Celery/Redis + PostgreSQL + TeX Live compilation), not yet a research-intelligence platform. Its three planned features — (A) VTOP integration + academic repository, (B) a Research Intelligence LLM over the university archive, and (C) a hosted Git platform — are what turn it into one.

The central research thesis of this agenda:

> **Most institutional repositories and research-intelligence systems model scholarly output primarily as static *products* such as final PDFs and metadata records. The documented educational capstone portal is designed to preserve more of the *process*: an append-only `AuditLog` on state transitions, monotonic report versions with compile history, immutable per-faculty scores, dual-path registration provenance (`registration_source`), team-formation handshakes, and capacity-constrained guide allocation. This makes it a candidate process-aware, provenance-rich academic project graph for questions that product-only repositories do not directly expose.**

That thesis is the differentiator. When VTOP adds longitudinal cross-cohort data, the Research Intelligence LLM adds semantic reasoning, and the Git platform adds code-artifact lineage, Educational Capstone Portal becomes a **multi-modal academic digital twin of the entire project lifecycle** — students, faculty, ideas, teams, code, theses, scores, and the audit trail that links them causally.

**Highest-leverage publishable directions (preview):**
1. **Process-aware academic project digital twin** built on the AuditLog (no product-only repo can do this).
2. **GraphRAG over an institutional research KG** with **provenance-verified citations** grounded in real records.
3. **Capacity-constrained heterogeneous-GNN faculty–student guide matching** (a constrained link-prediction problem the literature under-serves).
4. **LLM-as-reviewer calibration + grading-fairness auditing** validated against Educational Capstone Portal's immutable human score ground truth.
5. **Multi-modal artifact retrieval** across code ↔ thesis ↔ score ↔ outcome-plan.

> **Reality check (updated through September 2026):** None of these directions should be presented as categorically first. Attributed or verifiable RAG, LLM-versus-human grading, capacity-aware matching, educational process mining, and educational digital twins all have relevant prior work. The most defensible Team 1 direction is a capstone-specific evaluation of cross-object process observability on a documented transactional lifecycle, with explicit comparisons to case-centric projections and the closest educational object-centric baseline.

**What is engineering vs. research.** VTOP sync, GitLab hosting, OCR wiring, and malware scanning (G1–G3) are *engineering*. The *research* lives in what you do with the resulting data: the graph structure, the provenance chain, the evaluation ground truth, and the multi-modal artifact links.

---

## 2. Understanding of Educational Capstone Portal

### 2.1 What the system is
An asynchronous FastAPI backend managing capstone projects from **registration → compilation → three-stage submission → faculty review → immutable scoring → finalization**, with an audit row written on **every** transition.

### 2.2 Principal actors (from `actors-and-roles.md`)
- **Authenticated principals:** Student, Team Leader (a `role='leader'` value, not a separate identity), Faculty (holding ≥1 role), Admin.
- **Faculty roles (CHECK-constrained):** `guide`, `panel_member`, `project_coordinator`, `hod`, `dean` — scoped by `school_id`, `department_id`, `programme_code`.
- **Service/system actors:** Report Processing Service (Celery, `system_actor='CELERY_WORKER'`), Notification event bus, Audit Logger, Redis. **Planned/absent:** OCR (G1), Turnitin (G2), Security Scanner (G3).

### 2.3 Core workflows
- **Dual registration converging on one `Project`:** student-idea path (with member-confirmation handshake + team lock-on-submit) and faculty-proposal path (no handshake); `registration_source ∈ {student_idea, faculty_proposal, manual}`.
- **Report processing:** ZIP upload → inline validation → new `ReportVersion` → async LaTeX compile (Celery) with **SSE progress** and **SHA-256 content-hash caching**; compile failures are **free** (do not consume attempts).
- **Submission state machine:** `NOT_SUBMITTED → SUBMITTED → UNDER_VERIFICATION → ACCEPTED | (reject → NOT_SUBMITTED)`, **max 3 attempts/stage**, each rejection `max_tries−−, version++`.
- **Review & scoring:** guide accepts/rejects and records a **write-once, immutable** score under a `SERIALIZABLE` transaction (unique `(report_version_id, faculty_id)`); a second write returns HTTP 400. Examination subsystem (coordinator/panel/HOD) manages `ReviewMark` (`draft→confirmed→locked`) and re-review applications.

### 2.4 Database design (from `domain-model.md`)
Principals (`students`, `faculty`, `faculty_roles`) → registration (`student_project_ideas`, `student_project_idea_members`, `faculty_project_proposals`, `projects`, `student_project`) → submission (`project_reports` [R1/R2/R3], `project_report_versions`, `project_report_artifacts` [ppt/poster/sdg_plan/outcome_plan/outcome_status/outcome_attainment_proof]) → `scores`, `audit_log`, `faculty_guide_capacity`. Examination/venue subsystems (`review_events/panels/marks`, `rereview_applications`, `venue_bookings`, `visibility_lock`) exist in code (G11). **Source code = version `zip_path`; report = version `pdf_path` — there is no dedicated `source_code`/`final_report` artifact type.**

### 2.5 Current "AI pipeline"
Effectively **none yet.** Scoring is manual; OCR (G1) and Turnitin (G2) are planned-and-absent; the "Security Scanner" is inline structural ZIP validation only (G3). The Research Intelligence LLM (feature B) is greenfield.

### 2.6 Integrations
Google OAuth + JWT; TeX Live Docker for compilation; Redis for rate-limit/SSE/task metadata. **Planned:** VTOP sync, hosted Git (GitLab).

### 2.7 Limitations (the graphify + gap register make these unusually explicit)
- **G5** three-stage advancement (R1→R2→R3) is **not wired** — every report is stuck at R1.
- **G6/E15** two coexisting data models (legacy vs modular) with cross-model write-skew risk.
- **G9/E1** attempts-exhausted **deadlock** (`max_tries==0`).
- **G4/E6** no editable/before-after score storage → blocks safe OCR/Turnitin automation.
- **G3** no malware/vulnerability scanning of archives compiled in a TeX Live container.
- **E14** no conflict-of-interest guard (faculty-who-is-admin can approve own proposal).
- **G10** "one active idea/team per student" enforced only in application layer.

### 2.8 Architecture analysis — the research-relevant substrate
The gap register reads as a liability list, but for a *research* platform it is an asset inventory:

| Educational Capstone Portal mechanism | Product-only repos have… | Research asset it creates |
|---|---|---|
| `AuditLog` on every transition | final artifact only | **Longitudinal process/provenance dataset** (digital twin, process mining, anomaly detection) |
| Monotonic `ReportVersion` + compile history | one PDF | **Writing-process / revision-trajectory dataset** |
| Immutable per-faculty `scores` | no grades | **Evaluation ground truth** for LLM-judge calibration & fairness auditing |
| `registration_source` + team handshakes | no team graph | **Collaboration & supervision graph** for GNN link prediction |
| `faculty_guide_capacity` | none | **Constrained assignment** research (fairness/load) |
| Multi-artifact per version (+planned code) | PDF only | **Multi-modal artifact graph** (code↔thesis↔score↔outcome) |
| Outcome artifacts (SDG/CO-PO plans) | none | **Accreditation-outcome auto-mapping** dataset |

---

## 3. Architecture Analysis (planned-feature view)

**Feature A — VTOP Integration + Academic Repository.** Positions Educational Capstone Portal as a **Current Research Information System (CRIS)** / institutional repository, but *process-aware*. Engineering: VTOP sync, metadata extraction, version tracking. Research surface: metadata extraction under weak supervision; entity resolution across VTOP/Git/reports; FAIR/semantic-repository modeling; the provenance graph.

**Feature B — Research Intelligence LLM.** The core research vehicle. Sub-capabilities map cleanly to literatures: research discovery (dense retrieval + GraphRAG), faculty recommendation (expert finding + heterogeneous GNN), similar-project retrieval (scientific-document embeddings), topic suggestion & gap identification (KG structural holes + trend forecasting), literature recommendation (citation recommendation). Key **[ASSUMPTION]**: archive scale is university-scale (10⁴–10⁵ artifacts), favoring **SLM + RAG/GraphRAG over full fine-tuning**, and on-prem for privacy.

**Feature C — Hosted Git Platform.** Turns Educational Capstone Portal into a **Mining-Software-Repositories (MSR)** site with the rare advantage of linked *grades and theses*. Research surface: code↔thesis alignment, code-evolution intelligence, student collaboration analytics, code provenance/plagiarism, curriculum-to-code mapping.

---

## 4. Literature Survey

### Topic A — VTOP Integration + Academic Repository

**Landscape.** Institutional repositories and digital libraries (DSpace, EPrints, Fedora/Samvera) and the CRIS category are mature but **product-centric**: they catalogue finished artifacts with descriptive metadata (Dublin Core, OpenAIRE/CERIF). Large-scale scholarly knowledge graphs — **OpenAlex** (Priem et al., 2022), the former **Microsoft Academic Graph** (Sinha et al., 2015; Wang et al., 2020), Semantic Scholar's **S2ORC** (Lo et al., 2020), **ORKG** (Open Research Knowledge Graph, Jaradeh et al., 2019), and **CORE** — provide the citation/metadata backbone. Metadata extraction from PDFs uses **GROBID**, **CERMINE**, and increasingly LLM extraction; document-AI models **LayoutLM/LayoutLMv3** (Xu et al., 2020/2022), **Donut** (Kim et al., 2022), and **TrOCR** (Li et al., 2021) handle layout/OCR. FAIR data principles (Wilkinson et al., 2016) frame the metadata-quality target.

**State of the art.** Semantic/AI-augmented repositories (ORKG's machine-actionable contributions; scholarly-KG construction over S2ORC/OpenAlex); LLM-based metadata extraction reaching high field-level accuracy on clean PDFs.

**Datasets.** OpenAlex, S2ORC, unarXive, SciDocs, PubMed/PMC OA, DocBank/PubLayNet (layout).

**Limitations / open challenges.**
- Repositories are **snapshots of products**, not process; provenance is coarse (deposit event), not per-transition.
- Metadata extraction degrades on **institutional/thesis LaTeX** with local templates (e.g. the "VITSCOPE" template in Educational Capstone Portal) and regional-language content.
- **Entity resolution** across heterogeneous institutional sources (VTOP records ↔ Git repos ↔ thesis PDFs ↔ scores) is under-served — most KGs resolve within one modality.
- No standard for **linking a project's process trace to its final artifact.**

> **Educational Capstone Portal advance:** a repository whose atomic unit is the *versioned, audited project lifecycle*, not the deposited PDF.

---

### Topic B — LLM Trained on University Research Data

**RAG family.** **RAG** (Lewis et al., 2020) → dense retrieval **DPR** (Karpukhin et al., 2020), **ColBERT** (Khattab & Zaharia, 2020), **Contriever** (Izacard et al., 2022), **E5** (Wang et al., 2022); **Self-RAG** (Asai et al., 2024); RAG evaluation **RAGAS** (Es et al., 2024) and retrieval benchmark **BEIR** (Thakur et al., 2021).

**GraphRAG & KG+LLM.** Microsoft **GraphRAG** "From Local to Global" (Edge et al., 2024); **HippoRAG** (Gutiérrez et al., 2024); surveys on **KG-augmented LLMs / retrieval over graphs** (2023–2025). These add multi-hop, global-sensemaking, and structure the RAG index around communities — directly relevant since graphify already produces communities over Educational Capstone Portal.

**Fine-tuning / domain adaptation.** **LoRA** (Hu et al., 2022), **QLoRA** (Dettmers et al., 2023); instruction tuning **FLAN** (Wei et al., 2022), **Self-Instruct** (Wang et al., 2023); continued-pretraining **"Don't Stop Pretraining"** (Gururangan et al., 2020); scientific LMs **SciBERT** (Beltagy et al., 2019) and **Galactica** (Taylor et al., 2022, notable for hallucination lessons).

**Scientific document understanding & retrieval.** **SPECTER** (Cohan et al., 2020) → **SPECTER2 / SciRepEval** (Singh et al., 2023); **SciNCL** (Ostendorff et al., 2022) — citation-graph-contrastive document embeddings.

**Faculty / expert & research recommendation.** Expert-finding tradition (language-model & graph methods) now augmented with dense retrieval and GNNs; scientific-collaborator and reviewer-assignment work (e.g. the **Toronto Paper Matching System** lineage, affinity-based reviewer matching). **Citation recommendation:** content-based (Bhagavatula et al., 2018) and embedding/graph methods.

**Limitations / research gaps.**
- **Hallucinated citations** remain the signature failure of scholarly LLMs (post-Galactica); RAG mitigates but does not *verify* against authoritative records.
- Faculty/expert recommendation is usually **static and content-only**; it ignores **capacity, load, and conflict-of-interest** — all of which Educational Capstone Portal models natively (`faculty_guide_capacity`, E14).
- Domain adaptation studies rarely target **small, private, institutional corpora** with strong privacy constraints (the realistic university setting).
- GraphRAG evaluation lacks **provenance-grounded** correctness metrics ("is every claim traceable to a real record?").

> **Educational Capstone Portal advance:** provenance-verified GraphRAG where every generated claim resolves to an `audit_log`/record ID, and recommendation that is capacity- and conflict-aware by construction.

---

### Topic C — Hosted Git Platform for Academic Projects

**Landscape.** Educational Git platforms (GitHub Classroom, GitLab-EDU) and the **Mining Software Repositories (MSR)** field: commit/PR/issue mining, defect prediction, developer analytics. Code representation models: **CodeBERT** (Feng et al., 2020), **GraphCodeBERT** (Guo et al., 2021), **CodeT5** (Wang et al., 2021), and code LLMs (StarCoder, Code Llama, 2023–2024). Software provenance at scale: **Software Heritage** (Di Cosmo & Zacchiroli, 2017). Code plagiarism/similarity: MOSS lineage and learned clone detection.

**State of the art.** Code KGs / property graphs for vulnerability and understanding; GNNs over code graphs; repository-level code LLMs; commit-history analytics for developer behavior.

**Limitations / opportunities.**
- MSR overwhelmingly studies **open-source professional** repos; **student educational repos linked to grades and theses** are a rare, high-value setting Educational Capstone Portal creates.
- **Code↔document (thesis) alignment** — verifying that submitted code implements the method the thesis claims — is essentially unstudied at scale.
- **Collaboration analytics for learning** (who contributed what, equitably) is thin and ethically sensitive.
- Joint evaluation of provenance linking **code → report version → score → outcome artifact** remains limited in the reviewed educational-platform literature.

> **Educational Capstone Portal direction:** an integrated academic Git setting with linked grades, theses, and an audit trail, evaluated for code-to-thesis alignment and process-grounded collaboration analytics.

---

### Topic D — Process Mining, Object-Centric Event Logs & Temporal Graph Learning
*(Added after reviewer feedback — this is where Educational Capstone Portal's hardest-to-replicate novelty lives.)*

**Process mining.** The field's foundations: the **Process Mining Manifesto** (IEEE Task Force, van der Aalst et al., 2011) and van der Aalst's *Process Mining* (2016); core tasks are **process discovery** (event log → model: Alpha, Inductive, Heuristics, Fuzzy miners), **conformance checking** (log vs de-jure model), and **performance/predictive** mining. **PM4Py** (Berti et al.) is the reference Python library. **Educational Process Mining (EPM)** applies this to student/curricular event data — recent work builds **digital twins of student behaviour** from LMS logs and **curricular-trajectory analysis** (AIStudyBuddy, Roepke et al. 2024; Trajecta, PM4Py). These are the closest neighbours to Educational Capstone Portal's R1 — but they operate on **LMS clickstream / curricular records**, not on an **immutable per-transition submission-state-machine ledger**.

**Object-Centric Process Mining (OCPM) & OCEL 2.0 — the frontier fit for Educational Capstone Portal.** Traditional process mining forces a single `case_id`, so flattening to one lifecycle (Student *or* Team *or* Report) can duplicate or separate relationships involving the others. **OCEL 2.0** (Berti, Koren, Adams, Park, … van der Aalst, *OCEL 2.0 Specification*, arXiv:2403.01975, spec Oct 2023) allows one event to relate to **many objects of many types**, with **Event-to-Object (E2O)** and **Object-to-Object (O2O)** relationships and **dynamic (time-changing) object attributes**, and it defines a **relational SQLite** exchange format. This maps well onto the documented capstone domain: an event such as a guide accepting a submission may simultaneously concern Student, Team, Faculty, Project, ReportVersion, and Score objects. Miri et al. (2026) already establish direct educational object-centric prior work through PM4Moodle. The defensible Team 1 contribution is therefore a capstone-specific lifecycle model and an evaluation of which preregistered cross-object questions remain correct after case-centric projection, not a broad first-in-education claim.

**Temporal / dynamic graph learning.** An academic year is inherently temporal (teams form, ideas drop, guides change, code accrues), so **continuous-time dynamic graphs (CTDGs)** fit Educational Capstone Portal better than static heterogeneous GNNs. Key methods: **TGN** (Rossi et al., 2020) — per-node memory updated on every interaction (captures behavioural velocity, e.g. version churn); **TGAT** (Xu et al., 2020) — functional time encoding + attention (models time-decay of relevance, e.g. a guide's 2023 grading behaviour vs 2026); **DySAT** (Sankar et al., 2020) and **EvolveGCN** (Pareja et al., 2020) — discrete-time snapshot dynamics. **These should anchor R3 (guide matching), R10 (at-risk prediction) and R14 (collaboration prediction) instead of static HGT** — the temporal framing is both a better fit and a stronger novelty claim.

> **Educational Capstone Portal direction:** evaluate whether a capstone event ledger can be mapped to an object-centric event log and a continuous-time dynamic graph, enabling process and prediction questions that common CRIS/LMS/MSR exports do not directly expose.

---

## 4.5 Prior-Art Reality Check (Exa-verified, 2026-07-22)

Live literature search revised the novelty of five flagship ideas and surfaced the closest prior *system*. This section states honestly what already exists and what remains defensible for Educational Capstone Portal. **Net effect: the agenda's core thesis (process/provenance as the unit of record) holds, but several "high novelty" ideas drop to medium because the ML technique already exists — Educational Capstone Portal's edge is the *data substrate and setting*, not the method.**

### Baselines to compare against (corrected after reviewer feedback)
**⚠ DevProjAnalytics is NOT peer-reviewed — do not present it as "the SOTA system."** I verified it directly: it is a **Zenodo self-deposit** (Kazmi, Sarim & Mukhtar, COMSATS Islamabad, v1.0.0, 18 Mar 2026; a 182 kB PDF), *not* a conference/journal publication. It genuinely covers much of Educational Capstone Portal's planned *product* surface (BGE-M3 similarity + IP registration, DeBERTa AI-text detection, fine-tuned CodeBERT AI-code detection at 98.3% val acc, GitHub contribution analytics, 9-role RBAC across FYP-0/1/2). **Position it as "a concurrent, self-published institutional implementation with overlapping objectives,"** and cite it as *related engineering*, not as the state of the art. Educational Capstone Portal's differentiation still holds: DevProjAnalytics is *product + detection* focused — it has no immutable per-transition audit ledger, no submission-state-machine process model, and no dual-registration provenance.

**The real baselines to beat (mature, peer-reviewed / widely deployed):**
- **CRIS / research information systems — Symplectic Elements, Elsevier Pure** — heavily adopted, but *static record-keeping*: they record that a paper exists, not the versioned, audited process (failed compiles, rejected submissions, supervision handshakes) that produced it. Educational Capstone Portal's process-awareness is the gap.
- **GitHub Classroom / GitLab Education** — track code process but provide limited visibility into institution-specific grading rubrics, thesis alignment, or faculty-capacity/COI constraints. The proposed portal integration aims to **bridge the CRIS and MSR (Mining-Software-Repositories) worlds** with grade-linked, audited provenance.
- **GuruSetu** (Amrita, Neo4j graph matching w/ CGPA/batch constraints) and **thesis-supervisor recommenders** (Wijanto et al., JISEBI; Grapevine, 2020) — graph/IR student↔faculty matching already exists; tempers R3.

### Per-idea revision table
| Idea | Prior art found (2024–2026) | What's no longer novel | What remains defensible for Educational Capstone Portal | Revised novelty |
|---|---|---|---|---|
| **R2** Provenance-verified GraphRAG | RECLAIM (NAACL-F 2025), VeriCite (2025), MedGraphRAG (ACL 2025); GraphRAG-traceability eval (Ahmad 2026); "Traversal Context & Provenance in Agentic GraphRAG" (Terrenzi 2026) | Attributed/verifiable/citation-grounded RAG is a **crowded, active area**; "ground every claim to a source" is done | Grounding to **operational institutional records + `audit_log` IDs verifiable against a live DB** (not just a text passage), in the **academic-project domain** | High → **Medium-High** |
| **R3** Capacity/COI-aware guide matching | Reviewer-assignment w/ capacity+COI+fairness is classic (TPMS/CPAP; Charlin & Zemel); RevGNN (ACM TOIS 2024); COI-graph expert rec (MDPI 2023); student-supervisor rec (GuruSetu, Wijanto) | Capacity + COI + fairness constrained matching, and even student-supervisor matching, **already exist** | **`faculty_guide_capacity` as a live decrementing constraint** + **longitudinal outcome loop** (did the match yield a good grade/completion?) → *outcome-validated* matching | High → **Medium** |
| **R5** LLM-as-reviewer calibration | Abundant 2024: JGIM 2024, npj Sci Learn 2024, BMC Med Educ 2024, BJET 2024, arXiv 2406.16510, "Grading the Graders" 2024 — all correlate LLM vs human grades | "**Can LLMs grade / do they correlate with humans**" is **thoroughly studied** and mostly settled (moderate agreement, proportional bias) | Validation against an **immutable, audited, tamper-evident** ledger (vs small re-graded samples) + **coupling to human-bias auditing** on the *same* ground truth | High → **Medium** (pivot weight to R4) |
| **R7** Code↔thesis alignment | SciCoQA (ACL 2026, UKP), BioCon (2026), "Code Consistency via LLM+RAG" (2025) — paper-code discrepancy detection benchmarks | Paper-code consistency/discrepancy detection **now exists** (on research papers) | Apply to **student capstone theses with faculty-grade ground truth**; academic-integrity/assessment framing; grade-correlated | High → **Medium-High** |
| **R9** KG structural-hole gap ID | ResearchLink (Knowledge-Based Systems 2025 — hypothesis gen as KG link prediction + path/KGE/text features), ResearchAgent (NAACL 2025), HypER (EMNLP 2025) | Automated gap/hypothesis generation over scholarly KGs **exists** and is well-formalized | **Institutional** project-KG (not global science) to guide **student topic selection**, grounded in **real supervised-project outcomes** | High → **Medium-High** |
| **R1** Process-aware digital twin | Educational Process Mining digital twins on **LMS/curricular** logs (EPM digital-twin framework; AIStudyBuddy, Roepke 2024; Trajecta) | Digital twins of *student behaviour from LMS clickstream/curricular events* exist | Twin of a **project-submission state machine** from an **immutable per-transition audit ledger** — a substrate EPM work does **not** have | **High (holds)** |

### Ideas that survived largely unthreatened
R4 (grading-fairness auditing on an *immutable* ledger — less crowded than LLM-grading), R6 (code+thesis+**grade** joint retrieval), R8 (project lineage), R10/R11 (process-signal early warning & revision analytics), R17 (audit-trail anomaly detection), R22 (federated multi-campus KG), R27 (process-aware benchmark release), and R28 (cross-object observability). These lean on study-specific process evidence rather than claims that a method or dataset is universally unique. R28 is the strongest fit for the current Team 1 prototype because it already has a reproducible synthetic baseline and a clear real-data validation path.

---

## 5. State-of-the-Art Comparison Tables

### 5.1 Repositories / CRIS / educational platforms
| System | Unit of record | Process / temporal provenance | Multi-modal (code+thesis+grade) | Capacity/COI-aware | Semantic/LLM layer |
|---|---|---|---|---|---|
| DSpace / EPrints | Deposited artifact | Deposit event only | No | No | Minimal |
| OpenAlex / S2ORC | Paper + citations | No | No | No | Embeddings (external) |
| ORKG | Machine-actionable contribution | No | No | No | Curated + LLM-assisted |
| **Symplectic Elements / Elsevier Pure** (CRIS) | Research output record | No (static harvest) | No | No | Limited |
| **GitHub Classroom / GitLab EDU** | Repo + commits | Code events only | Code only | No | No |
| Software Heritage | Source code object | Content provenance (code) | Code only | No | No |
| DevProjAnalytics (Zenodo 2026, *non-peer-reviewed*) | FYP submission | No audit ledger | Detection over code+text | No | Similarity + detectors |
| **Educational Capstone Portal (target)** | **Versioned, audited project lifecycle** | **Per-transition AuditLog → OCEL 2.0** | **Yes (code+thesis+grade+workflow)** | **Yes (guide_capacity, E14)** | **GraphRAG + Temporal-GNN + LLM** |

### 5.2 Research-assistant / RAG approaches
| Method | Multi-hop | Global sensemaking | Provenance-verified claims | Capacity/COI-aware rec |
|---|---|---|---|---|
| Vanilla RAG (Lewis 2020) | Weak | No | No | No |
| Self-RAG (Asai 2024) | Some | No | Self-reflection, not record-verified | No |
| GraphRAG (Edge 2024) | Yes | Yes | No | No |
| HippoRAG (2024) | Yes | Partial | No | No |
| **Educational Capstone Portal GraphRAG (target)** | **Yes** | **Yes (graphify communities)** | **Yes (record-ID grounded)** | **Yes (guide_capacity, E14)** |

### 5.3 Faculty / expert recommendation
| Approach | Signal | Capacity | Conflict-of-interest | Explainable |
|---|---|---|---|---|
| Content expert-finding | Text profile | No | No | Weak |
| Embedding similarity (SPECTER2) | Doc embeddings | No | No | Weak |
| Reviewer matching (TPMS lineage) | Affinity | Partial (load) | Partial | Weak |
| **Educational Capstone Portal HGNN (target)** | **Heterogeneous graph + text** | **Yes** | **Yes** | **Path-based** |

---

## 6. Research Gap Analysis

### 6.1 Feature A — VTOP + Academic Repository
| Gap | Existing work | Why insufficient | Novel opportunity | Pub. potential |
|---|---|---|---|---|
| Process-aware repository (lifecycle as unit) | DSpace, OpenAlex, ORKG | Product snapshots; no per-transition provenance | AuditLog → project digital twin / provenance graph | **High** |
| Institutional-template metadata extraction | GROBID, LayoutLMv3 | Trained on generic PDFs; fails on local LaTeX/regional text | Weak-supervised extractor tuned on VITSCOPE-style theses | Medium |
| Cross-source entity resolution (VTOP↔Git↔thesis↔score) | Intra-modal KG linking | Rarely spans heterogeneous institutional systems | Multi-modal ER with audit-trail anchors | **High** |
| FAIR + accreditation metadata (CO-PO/SDG) | FAIR principles | Not operationalized for outcome artifacts | Auto-map reports → outcome/SDG metadata | Medium–High |

### 6.2 Feature B — Research Intelligence LLM
| Gap | Existing work | Why insufficient | Novel opportunity | Pub. potential |
|---|---|---|---|---|
| Provenance-verified generation | RAG, Self-RAG, GraphRAG | Grounds on text, not verifiable records | Every claim → `audit_log`/record ID; verifiability metric | **High** |
| Capacity/COI-aware faculty rec | Expert finding, TPMS | Ignores load & conflict-of-interest | HGNN with capacity constraints + E14-style COI | **High** |
| SLM domain adaptation on small private corpora | LoRA/QLoRA, DSP | Benchmarks are large/public; privacy ignored | On-prem SLM distillation for a single university | Medium–High |
| KG-structural-hole gap identification | Trend analysis, ORKG | Descriptive, not predictive of *unexplored* niches | Structural-hole scoring over institutional KG | **High** |
| Trend forecasting from cohort topics | Bibliometric trend work | Uses global corpora, coarse time | Fine-grained per-term cohort topic forecasting | Medium |

### 6.3 Feature C — Hosted Git Platform
| Gap | Existing work | Why insufficient | Novel opportunity | Pub. potential |
|---|---|---|---|---|
| Code↔thesis alignment | Code LLMs, doc retrieval | No cross-artifact "does code match claims" task | Cross-modal alignment scored vs faculty grades | **High** |
| Grade-linked student MSR | MSR on OSS | No linked grades/outcomes | Process signals → outcome prediction (early warning) | **High** |
| Equitable collaboration analytics | Contribution mining | Not learning-focused or fairness-aware | Fair contribution attribution with audit provenance | Medium–High |
| Full-lineage provenance (code→score→outcome) | Software Heritage | Code only | End-to-end artifact lineage graph | Medium |

---

## 7. Novel Research Directions (30 ideas)

> Difficulty & Novelty are 1–10. "Data" = Educational Capstone Portal-derivable unless noted.

> **Evaluation-protocol standard (added after reviewer feedback).** Every idea must specify hard, reproducible metrics — never "expert judgment" alone. Defaults by task type: **Retrieval/recommendation** → Recall@K, NDCG@K, MRR, MAP, Hit-Rate (report K=5,10). **Capacity-constrained matching (R3)** → NDCG@K *plus* faculty-workload **Gini coefficient** and **Constraint-Violation Rate** (fraction of suggestions exceeding `faculty_guide_capacity`). **Fairness auditing (R4)** → **Demographic-Parity Difference** and **Equalized-Odds** against the immutable ledger, with ICC/κ for rater reliability. **Cross-modal alignment (R7)** → MRR/Recall@K retrieving the correct repo from a 1,000-project cohort given a thesis abstract, + F1 vs expert labels. **Gap/hypothesis ID (R9)** → *predictive* validation (do flagged gaps get filled in later cohorts?) + expert P@20 on a held-out gold set (cf. ResearchLink's CSKG-600). **Process mining (R1/R28)** → fitness, precision, generalization, conformance (token-replay / alignments). **Prediction (R10/R14)** → AUC/AP, calibration (ECE), lead time.

**R1. Process-Aware Academic Project Digital Twin.** *Problem:* repositories lose the lifecycle. *Method:* build a temporal graph from `audit_log` + version history; learn a state-transition model (temporal GNN / process mining, van der Aalst) enabling replay, simulation, and outcome counterfactuals. *Contribution:* a capstone-specific digital-twin design evaluated on a transactional, multi-object audit model and compared with existing educational digital-twin approaches. *Data:* AuditLog, ReportVersion, scores. *Metrics:* next-transition prediction accuracy, outcome-simulation fidelity, and process conformance. *Venues:* ACM LAK, IEEE TLT, EDM. *Diff 7 · Nov 7 · Medium-High pending real-data validation.*

**R2. Provenance-Verified GraphRAG over the Institutional KG.** *Problem:* scholarly LLMs hallucinate citations. *Method:* GraphRAG (Edge 2024) over graphify communities; constrain every generated claim to resolve to a record/audit ID; add a *verifiability* metric. *Contribution:* record-grounded verifiability, not just retrieval grounding. *Metrics:* claim-traceability rate, RAGAS faithfulness, hallucinated-citation rate. *Venues:* ACL/EMNLP, SIGIR, CIKM. *Diff 7 · Nov 9→7 · High→Medium-High.* ⚠ **Prior art (Exa):** attributed/verifiable RAG is crowded — RECLAIM (NAACL-F 2025), VeriCite (2025), MedGraphRAG (ACL 2025), GraphRAG-traceability eval (2026). *Differentiate on:* grounding to verifiable **DB records + `audit_log` IDs**, not text passages.

**R3. Capacity-Constrained Heterogeneous-GNN Guide Matching.** *Problem:* faculty rec ignores capacity & COI. *Method:* HGNN (HGT, Hu et al. 2020) over student–idea–faculty–role graph + text; decode under `faculty_guide_capacity` and COI (E14) as a constrained assignment. *Contribution:* recommendation-as-constrained-matching with fairness. *Metrics:* match quality, load balance (Gini), COI violations, acceptance rate. *Venues:* RecSys, IEEE TLT, SIGIR. *Diff 7 · Nov 9→6 · High→Medium.* ⚠ **Prior art (Exa):** capacity+COI+fairness matching is classic (TPMS/CPAP; RevGNN, ACM TOIS 2024); student-supervisor rec exists (GuruSetu, Wijanto). *Differentiate on:* live decrementing `faculty_guide_capacity` + **outcome-validated** matching (match → grade/completion loop).

**R4. Grading-Fairness & Reviewer-Calibration Auditing from Immutable Scores.** *Problem:* grading bias is hard to study without ground truth. *Method:* hierarchical models over `scores`/`review_marks` to detect guide/panel disparities controlling for project features; calibrate raters. *Contribution:* fairness audit on genuinely immutable, audited scores. *Metrics:* inter-rater reliability, disparity effect sizes, calibration error. *Venues:* LAK, EDM, AIED, FAccT. *Diff 6 · Nov 8 · High.*

**R5. LLM-as-Reviewer Calibration Benchmark.** *Problem:* existing LLM-grading studies do not necessarily use the same longitudinal, audited capstone evidence available to this project. *Method:* prompt or fine-tune judges to score reports; correlate with immutable faculty scores; measure bias against the rubric. *Contribution:* evaluation of an LLM reviewer against an audited capstone assessment ledger, coupled with human-rater calibration rather than a broad first-of-kind claim. *Metrics:* Spearman/Kendall versus faculty, bias by group, and rubric grounding. *Venues:* EMNLP, AIED, NeurIPS D&B. *Diff 5 · Nov 5 · Medium.* ⚠ **Prior art:** LLM-versus-human grading is thoroughly studied. *Differentiate on:* the immutable audited ledger as ground truth and coupling with human-bias auditing (R4). Lead with R4, not R5.

**R6. Multi-Modal Academic Artifact Retrieval (code↔thesis↔score↔outcome).** *Problem:* retrieval is often evaluated within one artifact modality. *Method:* joint embedding across `zip_path` code, `pdf_path` thesis, artifacts, and scores; cross-modal contrastive training. *Contribution:* a capstone-specific retrieval benchmark linking code, thesis, assessment, and outcome evidence, evaluated against strong cross-modal baselines. *Metrics:* cross-modal MRR/nDCG and retrieval-to-grade correlation. *Venues:* SIGIR, ECIR, MM. *Diff 7 · Nov 6 · Medium-High pending data access.*

**R7. Code↔Thesis Semantic Alignment ("does the code implement the claimed method?").** *Method:* align thesis method sections with repo functions using CodeT5/GraphCodeBERT + LLM verification; validate against faculty acceptance. *Contribution:* new cross-modal alignment task + dataset. *Metrics:* alignment F1 vs expert labels, correlation with grades. *Venues:* MSR, ICSE-SEET, EMNLP. *Diff 8 · Nov 9→7 · High→Medium-High.* ⚠ **Prior art (Exa):** paper-code discrepancy detection now exists — SciCoQA (ACL 2026, UKP), BioCon (2026), Code-Consistency-via-LLM+RAG (2025). *Differentiate on:* **student theses with faculty-grade ground truth** + academic-integrity framing (not published research papers).

**R8. Semantic Project Lineage / Genealogy.** *Problem:* follow-on projects reuse/extend prior ones invisibly. *Method:* build a lineage graph via embedding + citation + advisor links; detect "descendant" projects across cohorts. *Contribution:* institutional research genealogy. *Metrics:* lineage-edge precision vs advisor annotations. *Venues:* JCDL, TPDL, IEEE TLT. *Diff 6 · Nov 8 · Medium–High.*

**R9. Research-Gap Identification via KG Structural Holes.** *Method:* compute structural-hole/Burt-style scores + embedding voids over the institutional KG to surface unexplored topic niches; validate with faculty. *Contribution:* predictive gap-finding vs descriptive trend reports. *Metrics:* expert-rated novelty/plausibility of proposed gaps. *Venues:* CIKM, ASONAM, Scientometrics (Springer). *Diff 7 · Nov 9→7 · High→Medium-High.* ⚠ **Prior art (Exa):** gap/hypothesis generation over scholarly KGs exists — ResearchLink (Knowledge-Based Systems 2025, link-prediction + path/KGE/text), ResearchAgent (NAACL 2025), HypER (EMNLP 2025). *Differentiate on:* **institutional** project-KG guiding **student** topic choice, grounded in real supervised-project outcomes.

**R10. Early-Warning "Project-at-Risk" from Process Signals.** *Method:* features from compile-failure counts, version churn, rejection attempts (`max_tries`), handshake delays → predict late/failed projects; survival analysis + temporal GNN. *Contribution:* process-signal early warning (not LMS clickstream). *Metrics:* AUC, lead time, calibration. *Venues:* LAK, EDM, IEEE TLT. *Diff 5 · Nov 7 · High.*

**R11. Writing-Process Analytics from Report-Version Deltas.** *Method:* diff consecutive `ReportVersion` PDFs/LaTeX; model revision trajectories → outcome. *Contribution:* revision-behavior dataset linked to grades. *Metrics:* trajectory-to-grade predictive power. *Venues:* LAK, Writing Analytics, CHI. *Diff 6 · Nov 7 · Medium–High.*

**R12. On-Prem SLM Distillation for a Private Research Assistant.** *Method:* distill a large teacher into a small on-prem model via QLoRA + synthetic institutional instructions; measure privacy/cost/quality trade-off. *Contribution:* realistic single-university SLM recipe. *Metrics:* task accuracy vs params/cost, leakage tests. *Venues:* EMNLP Industry, NAACL, IEEE Access. *Diff 6 · Nov 6 · Medium–High.*

**R13. Trend Forecasting of Cohort Research Topics.** *Method:* per-term topic modeling (BERTopic) + temporal forecasting of emerging areas. *Contribution:* fine-grained institutional trend forecasting. *Metrics:* forecast MAE, emergence lead time. *Venues:* Scientometrics, ASONAM, CIKM. *Diff 5 · Nov 6 · Medium.*

**R14. Faculty Collaboration / Co-Supervision Prediction.** *Method:* temporal link prediction over the faculty co-supervision graph (TGN, Rossi et al. 2020). *Contribution:* predicts cross-department collaboration from project data. *Metrics:* link-pred AP/AUC, realized-collab precision. *Venues:* ASONAM, SNAM (Springer), RecSys. *Diff 6 · Nov 7 · Medium–High.*

**R15. Institutional Citation Recommendation.** *Method:* fine-tune SciNCL/SPECTER2 on the local citation graph; recommend references for a submitted idea/report. *Contribution:* local-corpus citation rec + cold start. *Metrics:* Recall@k/MRR, expert relevance. *Venues:* JCDL, SIGIR, ECIR. *Diff 5 · Nov 6 · Medium.*

**R16. Cross-Cohort Semantic Idea-Reuse / Plagiarism Detection.** *Method:* embedding + graph detection of idea reuse across cohorts beyond string similarity (Turnitin). *Contribution:* semantic, cross-year academic-integrity detection. *Metrics:* PR vs adjudicated cases, robustness to paraphrase. *Venues:* IEEE TLT, EDM, ACM SAC. *Diff 6 · Nov 7 · Medium–High.*

**R17. Audit-Trail Anomaly & Integrity Monitoring.** *Method:* sequence models over `audit_log` to flag anomalous transition patterns (e.g. E14 self-approval, grade-tamper attempts). *Contribution:* process-anomaly detection for academic governance. *Metrics:* anomaly AUC, injected-attack detection. *Venues:* CIKM, IEEE TDSC, DFRWS. *Diff 6 · Nov 7 · Medium–High.*

**R18. Team-Formation → Collaboration-Success Modeling.** *Method:* from member handshakes/roles predict team outcome; study composition effects. *Contribution:* team-science on capstone teams with grades. *Metrics:* outcome prediction, causal composition effects. *Venues:* CSCW, LAK, SNAM. *Diff 6 · Nov 7 · Medium–High.*

**R19. Accreditation Outcome (CO-PO / SDG) Auto-Mapping.** *Method:* map report content to `outcome_plan/sdg_plan` artifacts and CO-PO/SDG rubrics via LLM + weak supervision. *Contribution:* automates accreditation evidence (NBA/NAAC-relevant). *Metrics:* mapping F1 vs coordinator labels. *Venues:* IEEE TLT, ACM SIGCSE, FIE. *Diff 5 · Nov 7 · Medium–High.*

**R20. Multi-Agent Research-Supervision Assistant.** *Method:* planner/retriever/critic agents over the institutional KG to draft supervision feedback, grounded and provenance-checked. *Contribution:* multi-agent supervision with record grounding. *Metrics:* faculty-rated usefulness, factuality. *Venues:* AIED, EMNLP (agents), CHI. *Diff 7 · Nov 8 · Medium–High.*

**R21. Panel-Assignment Optimization (conflict-free, expertise-matched, load-balanced).** *Method:* expertise embeddings + ILP/matching for `review_panels`. *Contribution:* examiner assignment with COI + load + expertise jointly. *Metrics:* expertise coverage, COI violations, load Gini. *Venues:* RecSys, EAAI, IEEE TLT. *Diff 5 · Nov 6 · Medium.*

**R22. Federated / Privacy-Preserving Multi-Campus Research KG.** *Method:* federated embeddings/GNN across VIT campuses without pooling raw data. *Contribution:* privacy-preserving inter-campus research intelligence. *Metrics:* federated vs central utility gap, privacy budget. *Venues:* IEEE TKDE, WWW, TPDL. *Diff 9 · Nov 8 · High (PhD-scale).*

**R23. Explainable Similar-Project Retrieval with Provenance Evidence.** *Method:* retrieval + path-based explanations over the KG ("similar because shared method X, advisor Y, dataset Z"). *Contribution:* explainable scholarly retrieval grounded in records. *Metrics:* explanation faithfulness, user trust. *Venues:* SIGIR, ECIR, IUI. *Diff 6 · Nov 7 · Medium–High.*

**R24. Concept-Drift Tracking of Project Topics Across Terms.** *Method:* embedding drift detection over cohorts; visualize topic evolution. *Contribution:* longitudinal concept-drift analytics for a curriculum. *Metrics:* drift-detection accuracy, alignment with curriculum changes. *Venues:* EDM, LAK, Scientometrics. *Diff 5 · Nov 6 · Medium.*

**R25. Code-Evolution Intelligence for Student Repos.** *Method:* commit-graph + code-embedding trajectories → learning/productivity signals; predict outcome. *Contribution:* MSR on grade-linked student repos. *Metrics:* outcome AUC, effort/quality proxies vs grades. *Venues:* MSR, ICSE-SEET, EDM. *Diff 7 · Nov 8 · High.*

**R26. Rubric-Grounded Explainable Scoring Recommendation.** *Method:* generate draft scores with rubric-cited rationales (closing G4's editable-value need); human-in-the-loop correction. *Contribution:* explainable, correctable AI scoring integrated with immutability. *Metrics:* faculty agreement, correction rate, rationale quality. *Venues:* AIED, LAK, EAAI. *Diff 6 · Nov 7 · Medium–High.*

**R27. Benchmark & Dataset Release: "AcaProc" — a process-aware academic project corpus.** *Method:* privacy-preserving, anonymized/synthetic release of Educational Capstone Portal's process+artifact graph as a community benchmark. *Contribution:* a reproducible capstone-process dataset with explicit schema, task definitions, and provenance. *Metrics:* task suite baselines; utility-vs-privacy. *Venues:* NeurIPS Datasets & Benchmarks, JCDL, LAK. *Diff 7 · Nov 8 · Medium-High.*

**R28. OCEL 2.0 Observability for Educational Capstone Lifecycles (Object-Centric Process Mining).** *Problem:* flattening an audit trail to a single `case_id` can lose or distort Student/Team/Faculty/Report context. *Method:* export the capstone lifecycle to **OCEL 2.0** (Berti et al. 2024) with E2O/O2O relationships and dynamic object attributes; compare the complete representation with project-, student-, and report-version-centric projections; and measure Cross-Object Observability Coverage over preregistered risk predicates. *Contribution:* a capstone-specific multi-object schema, documentation-grounded validation design, and reproducible synthetic benchmark that extend rather than duplicate the educational object-centric approach of Miri et al. (2026). *Metrics:* predicate computability and agreement with the object-centric oracle, relation preservation, conformance detection, runtime, and missingness sensitivity. *Venues:* **ICPM**, LAK, IS journals. *Diff 6 · Nov 8 · Medium-High pending real-log validation.*

**R29. Temporal-Graph Learning over the Evolving Academic Graph.** *Problem:* static HGT ignores that teams/guides/code evolve within and across semesters. *Method:* model Educational Capstone Portal as a **continuous-time dynamic graph**; apply **TGN** (node memory for behavioural velocity), **TGAT** (time-decay attention), and snapshot models (**DySAT**, **EvolveGCN**) to guide-matching (R3), at-risk prediction (R10), and collaboration prediction (R14). *Contribution:* temporal-GNN reframing of academic-lifecycle prediction with a real evolving graph. *Metrics:* temporal AP/AUC, time-aware NDCG, lead time, calibration. *Venues:* LoG, ASONAM, WWW, IEEE TLT. *Diff 7 · Nov 8 · High.*

**R30. Systems: Memory-Efficient On-Prem Agentic Orchestration + High-Speed Temporal-Graph Query Engine.** *Problem:* running on-prem multi-agent evaluation (privacy) while doing multi-hop temporal traversals saturates commodity RAM, and PostgreSQL chokes on deep temporal graph queries. *Method:* memory-efficient agent scheduling (weight residency vs concurrent traversal), plus a Rust/systems-language analytical query layer for approximate multi-hop temporal traversal, targeting 10–100× over the Python/FastAPI path. *Contribution:* a systems architecture for real-time process-aware academic KGs. *Metrics:* query latency/throughput, memory footprint, approximation error, agent-loop cost. *Venues:* VLDB/SIGMOD/ICDE/EDBT (demo or research), IEEE Access. *Diff 8 · Nov 7 · Medium-High.*

---

## 8. Publishable Feature Ideas (32 features)

> Each is buildable into Educational Capstone Portal **and** carries a research contribution. Format: *why → implementation → AI/ML → novelty → related → gap → venue.*

1. **Semantic archive search.** Students find prior projects. Dense retrieval (SPECTER2/E5) + reranker. *Novelty:* institutional-tuned scientific retrieval. *Rel:* BEIR, SPECTER2. *Gap:* local-corpus adaptation. *Venue:* SIGIR/ECIR.
2. **"Find my guide" recommender.** Match students to guides. HGNN + capacity decode. *Novelty:* capacity/COI-aware. *Rel:* TPMS, HGT. *Gap:* constrained rec. *Venue:* RecSys/IEEE TLT.
3. **Duplicate-idea detector at registration.** Prevent redundant projects. Embedding + threshold + graph. *Novelty:* real-time semantic dedup with cross-cohort memory. *Rel:* clone/plagiarism detection. *Gap:* cross-year semantic. *Venue:* ACM SAC/IEEE TLT.
4. **Auto literature recommendation for a submitted idea.** Kick-start lit review. Citation rec (SciNCL) + RAG. *Novelty:* idea→reference cold start. *Rel:* Bhagavatula 2018. *Gap:* local + cold start. *Venue:* JCDL.
5. **Departmental research-gap dashboard.** Coordinators see white space. Structural holes + embedding voids. *Novelty:* predictive gap map. *Rel:* ORKG, scientometrics. *Gap:* prescriptive gaps. *Venue:* CIKM/Scientometrics.
6. **Thesis metadata auto-extraction (FAIR cards).** Clean catalog. LayoutLMv3/GROBID + LLM on VITSCOPE template. *Novelty:* institutional-template robustness. *Rel:* GROBID. *Gap:* local LaTeX. *Venue:* JCDL/TPDL.
7. **AI-assisted rubric scoring suggestions.** Speed + consistency. LLM-judge + rubric grounding, draft-only. *Novelty:* validated vs immutable grades. *Rel:* Zheng 2023. *Gap:* real-grade validation. *Venue:* AIED.
8. **Institutional similarity engine (Turnitin alternative).** In-house originality. Embedding + n-gram + code clones. *Novelty:* multi-modal (text+code) originality. *Rel:* MOSS, dense retrieval. *Gap:* combined text+code. *Venue:* IEEE TLT.
9. **Calibrated AI-content detection.** Flag AI-written reports responsibly. Detector + uncertainty + human review. *Novelty:* calibration + abstention for high-stakes. *Rel:* AI-text-detection limits. *Gap:* calibrated academic use. *Venue:* EMNLP/FAccT.
10. **OCR score extraction + HITL correction (G1/G4).** Kill manual entry. TrOCR/Donut + editable-value store. *Novelty:* extraction reconciled with score immutability. *Rel:* TrOCR. *Gap:* correctable audited extraction. *Venue:* DAS/ICDAR/AIED.
11. **Project lineage explorer.** Visualize research ancestry. Lineage graph (R8) + UI. *Novelty:* institutional genealogy UI. *Rel:* citation genealogy. *Gap:* project-level lineage. *Venue:* IEEE VIS/TPDL.
12. **Faculty collaboration recommender.** Spark cross-dept work. Temporal link prediction. *Novelty:* project-derived collab signal. *Rel:* TGN. *Gap:* capstone-derived. *Venue:* ASONAM.
13. **Emerging-topic radar.** Coordinators track trends. BERTopic + forecasting. *Novelty:* per-term granularity. *Rel:* bibliometrics. *Gap:* fine-grained. *Venue:* Scientometrics.
14. **Project-at-risk early warning.** Intervene early. Process-signal survival model (R10). *Novelty:* process not clickstream. *Rel:* LA early warning. *Gap:* audit-derived. *Venue:* LAK.
15. **Report-draft writing assistant.** Improve theses. Retrieval-grounded feedback LLM. *Novelty:* grounded in prior graded reports. *Rel:* writing analytics. *Gap:* corpus-grounded feedback. *Venue:* CHI/LAK.
16. **Git code quality & plagiarism analytics.** Fair code assessment. Static analysis + clone GNN. *Novelty:* grade-linked. *Rel:* MSR. *Gap:* educational grade-linked. *Venue:* MSR/SEET.
17. **Project→publication linkage.** Track impact. Entity resolution to OpenAlex/Scholar. *Novelty:* capstone→paper linkage. *Rel:* OpenAlex. *Gap:* project provenance. *Venue:* JCDL/Scientometrics.
18. **Auto faculty expertise profiles.** Keep profiles current. Aggregate supervised corpus → embeddings. *Novelty:* supervision-derived expertise. *Rel:* expert finding. *Gap:* auto from projects. *Venue:* SIGIR/IEEE TLT.
19. **Panel-assignment optimizer.** Fair exams. ILP + expertise (R21). *Novelty:* COI+load+expertise joint. *Rel:* reviewer matching. *Gap:* exam panels. *Venue:* EAAI.
20. **Conversational research assistant.** Ask the archive. GraphRAG chatbot (R2). *Novelty:* provenance-verified. *Rel:* GraphRAG. *Gap:* record grounding. *Venue:* EMNLP/SIGIR.
21. **CO-PO / SDG auto-mapping.** Accreditation evidence (R19). LLM + weak supervision. *Novelty:* outcome-artifact mapping. *Rel:* — (thin). *Gap:* automated accreditation. *Venue:* FIE/SIGCSE.
22. **Cross-modal QA (code+report+score).** Deeper answers. Multi-modal RAG (R6). *Novelty:* joint-modality QA. *Rel:* multimodal RAG. *Gap:* code+thesis+grade. *Venue:* MM/SIGIR.
23. **Reviewer-calibration dashboard.** Grade fairness (R4). Hierarchical models. *Novelty:* immutable-score fairness. *Rel:* IRR studies. *Gap:* audited grades. *Venue:* LAK/FAccT.
24. **Provenance-verified answer citations.** Trust the assistant. Claim→record resolver (R2). *Novelty:* record-level verifiability. *Rel:* Self-RAG. *Gap:* verifiable. *Venue:* ACL/SIGIR.
25. **Auto related-work generation.** Draft lit reviews. RAG over institutional + external corpus. *Novelty:* grounded, non-hallucinated. *Rel:* Galactica lessons. *Gap:* verifiable synthesis. *Venue:* EMNLP.
26. **Student research navigator (topic→faculty→resource pathfinding).** Guide exploration. KG pathfinding + explanations. *Novelty:* explainable academic pathfinding. *Rel:* KG reasoning. *Gap:* institutional. *Venue:* IUI/AIED.
27. **Version-diff summarizer (R1→R2→R3).** See what changed. Diff + LLM summarize. *Novelty:* graded revision summaries. *Rel:* doc diff. *Gap:* thesis revisions. *Venue:* LAK/EMNLP.
28. **Auto viva/defense question generator.** Prep students/panels. Thesis-grounded QG. *Novelty:* defense-oriented QG from real theses. *Rel:* question generation. *Gap:* viva setting. *Venue:* AIED/BEA.
29. **Curriculum-to-research alignment.** Show courses→projects. KG alignment of syllabi to project topics. *Novelty:* curriculum-research graph. *Rel:* curriculum analytics. *Gap:* alignment. *Venue:* SIGCSE/LAK.
30. **Privacy-preserving archive export ("AcaProc" release, R27).** Enable external research. Anonymization/synthetic gen + utility eval. *Novelty:* process-aware academic benchmark. *Rel:* synthetic-data privacy. *Gap:* the dataset itself. *Venue:* NeurIPS D&B.
31. **Regional-language abstract generation & retrieval.** Inclusivity. Multilingual embeddings + MT. *Novelty:* Indic-language scholarly retrieval. *Rel:* multilingual IR. *Gap:* regional scholarly. *Venue:* ECIR/ACL (multilingual).
32. **Audit-integrity monitor.** Detect tampering/COI (R17). Sequence anomaly detection. *Novelty:* academic-governance anomaly detection. *Rel:* fraud detection. *Gap:* audit-trail security. *Venue:* IEEE TDSC/CIKM.

---

## 9. Research Roadmap

### 9.1 Top 10 Easiest Publications (fast, mostly application/eval; low infra risk)
1. **R5** LLM-as-reviewer calibration (needs only scores + reports).
2. **R15 / F4** Institutional citation recommendation (fine-tune SPECTER2/SciNCL).
3. **R13 / F13** Cohort trend forecasting (BERTopic + forecast).
4. **F1** Semantic archive search (retrieval + eval).
5. **R11 / F27** Report-version revision analytics / diff summaries.
6. **R19 / F21** CO-PO/SDG outcome auto-mapping (weak supervision).
7. **R4 / F23** Grading-fairness auditing (hierarchical models).
8. **F6** Thesis metadata extraction on VITSCOPE template.
9. **R10 / F14** Project-at-risk early warning (tabular + survival).
10. **R24** Concept-drift tracking across terms.

### 9.2 Top 10 Highest-Impact Papers *(reordered for the process-aware pivot — LLM/GraphRAG ideas demoted)*
1. **R28** Capstone-lifecycle observability under OCEL 2.0 and case-centric projection. → ICPM.
2. **R1** Process-aware academic-project digital twin (from the immutable audit ledger).
3. **R27 / F30** "AcaProc" reproducible process-aware benchmark release.
4. **R29** Temporal-graph learning over the evolving academic graph (TGN/TGAT).
5. **R6 / F22** Multi-modal artifact retrieval (code+thesis+**grade**+workflow).
6. **R2 / F20** Provenance-verified GraphRAG — *record-grounded*, institutional (now Medium-High).
7. **R7** Code↔thesis alignment on graded student theses.
8. **R25 / F16** Code-evolution intelligence on grade-linked student repos.
9. **R17 / F32** Audit-trail anomaly/integrity for academic governance.
10. **R3 / F2** Capacity/COI **temporal** guide matching (outcome-validated).

### 9.3 Top 10 Long-Term / PhD-Scale Ideas
1. **R22** Federated multi-campus research KG.
2. **R1** Full digital twin with counterfactual simulation.
3. **R2** Provenance-verified generation as a general paradigm (thesis-scale).
4. **R27** Sustained benchmark + task suite + community.
5. **R7** Cross-modal code↔thesis alignment at scale.
6. **R20** Multi-agent supervision assistant.
7. **R6** Unified multi-modal academic representation learning.
8. **R3** Constrained recommendation-as-matching theory + fairness.
9. **R12** On-prem SLM distillation recipe + privacy guarantees.
10. **R9 + R13** Predictive science-of-science over an institutional corpus.

### 9.4 Ranking rationale (summary) — revised after Exa verification
- **Novelty leaders (post-verification + reviewer pivot):** **R28** (capstone-lifecycle observability under object-centric and projected logs), **R1** (audit-ledger digital twin), **R27** (reproducible process-aware benchmark), **R29** (temporal-graph learning over the evolving academic graph), **R6** (code+thesis+**grade** retrieval), **R4** (fairness audit on immutable ledger), and **R17** (audit-trail anomaly analysis). These are hypotheses and study designs, not established firsts. Their strongest defensible value is the capstone setting, explicit provenance, and evaluation design; empirical novelty must be demonstrated against current educational object-centric baselines.
- **Feasibility leaders:** R4, R15, R13, F1, R11 (data already exists; no new infra).
- **Effort:** low (R4, R15, R13, R24, R11) · medium (R2, R3, R6, R9, R10) · high (R7, R22, R27, R20).
- **Publication probability × impact:** **R4** (not R5) is the best near-term ROI — it leans on the immutable ledger, the one asset with no close substitute; **R27** and **R1** are the best long-term bets. Treat R5 as a *supporting* replication, not a standalone paper.

---

## 10. Recommended First Paper

**Title (working):** *"Grading in the Open: Calibrating LLM Reviewers and Auditing Human Bias with an Immutable Academic Score Ledger."*

> **Post-verification pivot (Exa 2026-07-22):** LLM-vs-human grading (R5) turned out to be **heavily studied in 2024** — so lead with the *human grading-fairness audit* (R4) on the immutable ledger, which is far less crowded, and use LLM judges as a *calibrated instrument within* that audit rather than the headline contribution. The defensible novelty is the **tamper-evident audited score ledger as ground truth**, not "can an LLM grade."

**Why this one.** It leads with R4 (human grading-fairness auditing) supported by R5 (LLM judges as an instrument) and exploits Educational Capstone Portal's single most defensible asset — **write-once, `SERIALIZABLE`, per-faculty immutable scores with a full audit trail** — genuine, hard-to-fake evaluation ground truth that public corpora and the abundant 2024 "LLM-grading" studies lack (those use small, re-graded samples). It needs **no new infrastructure** (no VTOP, no Git, no OCR) and sidesteps the G1–G6 engineering gaps.

**Contributions.**
1. A **grading-fairness / rater-calibration audit** on genuinely immutable, audited faculty scores (guide vs panel disparities, controlling for project features) — the primary novel contribution.
2. LLM judges used as a **calibrated auxiliary rater** to triangulate human bias, with an honest replication of 2024 LLM-vs-human-grade findings *on an immutable-ledger setting* (contribution = the ledger methodology, not the correlation itself).
3. A **rubric-grounding** protocol that makes scores explainable and correctable — motivating the G4 editable-value design as a *finding*, not just an engineering gap.

**Method.** (a) Extract `(report_version → pdf, scores, review_marks, audit_log)`; (b) hierarchical/mixed-effects models for rater disparity + reliability; (c) prompt & LoRA-tuned LLM judges scoring reports; (d) correlate LLM vs faculty, measure bias by group and rubric grounding; (e) ablate retrieval-augmented rubric context.

**Evaluation.** Spearman/Kendall (LLM vs faculty), inter-rater reliability (ICC/κ), calibration error, disparity effect sizes, rubric-grounding faithfulness.

**Ethics/privacy.** IRB/committee approval, anonymization, no student-identifying release; report fairness findings responsibly. **[ASSUMPTION]** institutional data-use approval is obtainable.

**Target venues.** *AIED 2027* or *LAK 2027* (primary); *EDM* / *IEEE TLT* / *ACM FAccT* (alternates).

**Feasibility.** ~1 semester with existing data; main risk is score-volume sufficiency — mitigate by pooling across cohorts/terms.

---

## 11. References

*Established works underpinning this agenda (verify exact venue/year before manuscript submission):*

**RAG / retrieval / GraphRAG.** Lewis et al., *RAG*, NeurIPS 2020 · Karpukhin et al., *DPR*, EMNLP 2020 · Khattab & Zaharia, *ColBERT*, SIGIR 2020 · Izacard et al., *Contriever*, 2022 · Wang et al., *E5*, 2022 · Asai et al., *Self-RAG*, ICLR 2024 · Edge et al., *From Local to Global: GraphRAG*, 2024 · Gutiérrez et al., *HippoRAG*, NeurIPS 2024 · Thakur et al., *BEIR*, NeurIPS D&B 2021 · Es et al., *RAGAS*, EACL 2024.

**Scientific document understanding.** Beltagy et al., *SciBERT*, EMNLP 2019 · Cohan et al., *SPECTER*, ACL 2020 · Singh et al., *SciRepEval/SPECTER2*, 2023 · Ostendorff et al., *SciNCL*, 2022 · Taylor et al., *Galactica*, 2022 · Lo et al., *S2ORC*, ACL 2020 · Priem et al., *OpenAlex*, 2022 · Sinha et al./Wang et al., *Microsoft Academic Graph*, 2015/2020 · Jaradeh et al., *ORKG*, 2019.

**Fine-tuning / adaptation.** Hu et al., *LoRA*, ICLR 2022 · Dettmers et al., *QLoRA*, NeurIPS 2023 · Wei et al., *FLAN*, ICLR 2022 · Wang et al., *Self-Instruct*, ACL 2023 · Gururangan et al., *Don't Stop Pretraining*, ACL 2020.

**Graphs / GNNs (static).** Kipf & Welling, *GCN*, ICLR 2017 · Hamilton et al., *GraphSAGE*, NeurIPS 2017 · Wang et al., *HAN*, WWW 2019 · Hu et al., *HGT*, WWW 2020 · Zhang & Chen, *SEAL* link prediction, NeurIPS 2018.

**Temporal / dynamic graph learning.** Rossi et al., *Temporal Graph Networks (TGN)*, ICML-W 2020 · Xu et al., *Inductive Representation Learning on Temporal Graphs (TGAT)*, ICLR 2020 · Sankar et al., *DySAT*, WSDM 2020 · Pareja et al., *EvolveGCN*, AAAI 2020.

**Process mining & object-centric event logs.** van der Aalst et al., *Process Mining Manifesto*, BPM Workshops 2011 · van der Aalst, *Process Mining: Data Science in Action*, Springer 2016 · Berti et al., *PM4Py* (process-mining for Python) · **Berti, Koren, Adams, Park, … van der Aalst, *OCEL 2.0 Specification*, arXiv:2403.01975, 2024 (spec Oct 2023)** · Roepke et al., *AIStudyBuddy: study-path analysis with process mining*, Informatik Spektrum 2024 · educational-process-mining digital-twin & curricular-analysis works (Trajecta, PM4Py).

**Code / MSR.** Feng et al., *CodeBERT*, EMNLP-F 2020 · Guo et al., *GraphCodeBERT*, ICLR 2021 · Wang et al., *CodeT5*, EMNLP 2021 · Di Cosmo & Zacchiroli, *Software Heritage*, 2017.

**Document AI / OCR.** Xu et al., *LayoutLM(v3)*, 2020/2022 · Li et al., *TrOCR*, 2021 · Kim et al., *Donut*, ECCV 2022 · GROBID / CERMINE (tools).

**Evaluation / learning analytics / process.** Zheng et al., *LLM-as-judge / MT-Bench*, NeurIPS D&B 2023 · Piech et al., *Deep Knowledge Tracing*, NeurIPS 2015 · van der Aalst, *Process Mining* (2016) · Wilkinson et al., *FAIR Principles*, Sci. Data 2016 · Bhagavatula et al., *Content-based Citation Recommendation*, NAACL 2018.

### Prior art surfaced during Exa verification (2026-07-22) — cite these in the relevant papers

**Verified foundational (venue/year confirmed).** Ostendorff et al., *SciNCL: Neighborhood Contrastive Learning for Scientific Document Representations*, EMNLP 2022 · Singh et al., *SciRepEval / SPECTER2*, EMNLP 2023 (arXiv:2211.13308) · Gutiérrez et al., *HippoRAG*, NeurIPS 2024 (arXiv:2405.14831) · Asai et al., *Self-RAG*, ICLR 2024 (Oral) · Edge et al., *From Local to Global: A GraphRAG Approach to Query-Focused Summarization*, 2024–25 (arXiv:2404.16130).

**Attributed / verifiable RAG (threatens R2).** *RECLAIM* (Findings of NAACL 2025) — sentence-level citations via constrained decoding · *VeriCite* (arXiv:2510.11394, 2025) — NLI-verified citations · *MedGraphRAG* (ACL 2025) — evidence-linked GraphRAG · Ahmad et al., *Evaluating GraphRAG for Traceable and Interpretable QA* (2026) · Terrenzi et al., *Why Neighborhoods Matter: Traversal Context and Provenance in Agentic GraphRAG* (2026).

**Capacity/COI reviewer & supervisor matching (threatens R3).** *RevGNN* (ACM TOIS 2024, arXiv:2407.20684) · Charlin & Zemel, *Toronto Paper Matching System* lineage / CPAP (constrained assignment w/ capacity+COI) · *Perceiving Conflict-of-Interest Expert Recommendation* (Appl. Sci., MDPI 2023) · Wijanto et al., *Thesis Supervisor Recommendation* (JISEBI) · *GuruSetu* (Amrita, Neo4j graph mentor-matching) · Rahdari et al., *Grapevine* (2020).

**Paper–code alignment (threatens R7).** Baumgärtner & Gurevych, *SciCoQA: QA for Scientific Paper–Code Alignment*, ACL 2026 (UKPLab) · *BioCon: Paper-Code Consistency in Bioinformatics* (arXiv:2603.22018, 2026) · Keshri et al., *Enhancing Code Consistency in AI Research with LLMs and RAG* (arXiv:2502.00611, 2025).

**Research-gap / hypothesis generation (threatens R9).** Borrego et al., *ResearchLink: Hypothesis Generation over KGs* (Knowledge-Based Systems 2025; CSKG-600 dataset) · Baek et al., *ResearchAgent* (NAACL 2025) · *HypER: Literature-grounded Hypothesis Generation with Provenance* (EMNLP 2025).

**Concurrent systems & educational process mining.** *DevProjAnalytics* (Kazmi, Sarim & Mukhtar, COMSATS Islamabad — **Zenodo self-deposit v1.0.0, 18 Mar 2026, NOT peer-reviewed**; BGE-M3 similarity + DeBERTa AI-text detection + fine-tuned CodeBERT + GitHub analytics — cite as a *concurrent institutional implementation*, not SOTA) · **CRIS baselines: Symplectic Elements, Elsevier Pure** (static record-keeping) · **GitHub Classroom / GitLab Education** (code process, no grades/COI) · Roepke et al., *AIStudyBuddy: Study-path analysis with process mining* (Informatik Spektrum, 2024) · *A Digital Twin Framework for Analysing Students' Behaviours Using Educational Process Mining* · *Trajecta* (curricular process mining, PM4Py).

**LLM-vs-human grading (threatens R5).** Zhang et al., *Criterion-based grading with LLMs* (npj Science of Learning 2024) · Yavuz et al., *LLM EFL essay grading* (BJET 2024) · *ChatGPT AES for dental exams* (BMC Med Educ 2024) · Sreedhar et al. (J Gen Intern Med 2024/25) · Lundgren, *LLMs in Student Assessment* (arXiv:2406.16510, 2024) · Wetzler et al., *Grading the Graders* (2024).

---

### Appendix — graphify grounding
Derived from `graphify-out/` (182 nodes, 366 edges, 14 communities). God nodes (README, Project Registration, Domain Model, Report Processing, Submission System, State Machines, Faculty Review, ADR-004, G3, G4) confirm the process/state-machine/audit core that anchors the "process-aware" thesis. Gap hyperedges (attempts-exhausted deadlock, malware-scan gap, OCR/Turnitin pipeline) map directly onto the engineering-vs-research boundary in §1 and §6.
