# Journal Paper Research Plan — Team 1

**Working title:** *How Much Does Flattening Hide? Measuring Cross-Object Observability in Transactional Review Workflows with OCEL 2.0*
(Project title for Review 2 stays "Object-Centric Event Log Mining for Academic Capstone Processes: A Native OCEL 2.0 Approach"; the journal title may differ from the course title.)

**Drafted:** 2026-10-27 · **Status (updated same day):** Phase 1 data downloaded and checksum-verified into `realdata/raw/` (approved by the team); the first executable COOC experiments have run — see §13 for what they showed and how that changes this plan. Sections 1–12 are the original plan; where §13 contradicts them, §13 wins.

**Evidence classes used in this document** (extends the Review 2 rule): *Documented platform fact* · *External literature claim* · *Synthetic result* · **Public real-data result** (new — real, but not capstone) · *Proposed work*.

---

## 1. What the project is

| Item | Understanding |
|---|---|
| Domain | A capstone portal (FastAPI + Celery + PostgreSQL) with a three-stage report lifecycle R1→R2→R3, max 3 attempts per stage, write-once scores, an append-only `AuditLog`, and guide capacity limits. Documented in `docs/educational-capstone-platform/`. |
| Research question | Which cross-entity relationships and risk predicates stop being computable, or become silently wrong, when a multi-object lifecycle is flattened to one case notion? |
| Method | Native OCEL 2.0 model (Project, Team, Student, Faculty, Report, ReportVersion, Score), 6 preregistered risk predicates (G5, G9, E5, E10, E12, E15), a metric called **COOC** (Cross-Object Observability Coverage), a rule-based detector, a Markov next-step model, and an offline policy simulator. |
| Evidence so far | At Review 2: 100 % synthetic (120 projects × 3 scenarios, seed 4971) in a `synthetic/` folder that was **removed on 2026-10-27** (see §14). No production logs, no real PDFs. |
| Novelty boundary | Not "first OCEL in education" — Miri et al. (2026) did Moodle→OCEL. The defensible claim is a capstone-style *transactional review lifecycle* plus a task-level observability measure. |
| Team / guide | Aakaash Sathya Saravanan, Mitisha Sharma, Tanmay Khambete; Dr. Kalyanaraman P. |

---

## 2. Honest audit: what will not survive peer review as written

These are the reasons the current results cannot support a journal paper by themselves. All are fixable, and fixing them *is* the research work.

| # | Problem | Where | Why a reviewer will object |
|---|---|---|---|
| A1 | **COOC is hard-coded, not computed.** `observability_coverage()` returns literal dictionaries (2/6, 1/6, 3/6, 6/6). | `synthetic/src/analyze_team1_synthetic.py:167-192` | The paper's headline metric has no executable definition. A reviewer cannot reproduce 33.3 / 16.7 / 50.0 %. |
| A2 | **"Relation preservation" is near-tautological.** It counts the share of event→object rows whose object type equals the case type (`kept / total_links`). | `analyze_team1_synthetic.py:74-88` | No flat log is actually built; a project-centric view "keeps" only project links by construction. Real flattening (pm4py/ocpa) duplicates events (convergence) and repeats activities (divergence); neither is measured. |
| A3 | **Detector and generator share labels (leakage).** The generator writes `capacity_overrun`, `legacy_remaining`/`modular_remaining`, and `score_is_null` into `details_json`; the detector reads exactly those fields. | `team1_synthetic_ocel.py:118,152-154,184` ↔ `analyze_team1_synthetic.py:53-62` | Macro-F1 0.977 measures string matching, not detection. The lit review itself calls this circular. |
| A4 | **Twin outcomes are the inputs.** Deadlock/capacity/completion probabilities are typed constants (0.105, 0.018, …). | `analyze_team1_synthetic.py:139-145` | "Deadlock 11.2 % → 1.3 %" restates the parameters. Nothing is calibrated or inferred. |
| A5 | **Markov split is random, not chronological**, and 283 test transitions from 120 projects, one seed. | `analyze_team1_synthetic.py:96-99` | Contradicts the execution prompt's own "chronological split" rule; no CI. |
| A6 | **Only 6 of the 10 anomaly types** named in the execution prompt are injected (G7, E8, E9, E14 are not). | `team1_synthetic_ocel.py:88` | The "six preregistered predicates" were chosen after the generator was written, so they are not preregistered in any verifiable sense. |
| A7 | **No uncertainty anywhere**: one seed, one cohort size, no missingness or anomaly-rate sweep. | whole pipeline | Required by `Research_and_Novelty_Plan.txt` §4 itself. |
| A8 | **Housekeeping regression in the working tree.** `synthetic/results/experiment_summary.json` has `"disclaimer": ""` (HEAD has the synthetic-disclaimer string), and uncommitted edits strip the word "synthetic" from two docstrings. The analysis script still writes the disclaimer, so re-running restores it. | `git diff` | Moot: those uncommitted edits were discarded when `synthetic/` and `demo/` were deleted (§14). |

**Consequence for strategy:** a paper whose only evidence is this generator would be rejected. The paper needs (i) an executable, falsifiable COOC; (ii) evidence from **real public event data**; (iii) a synthetic benchmark whose labels are independent of the detector.

---

## 3. Paper positioning (what we can honestly claim)

**One paper, one claim.** Scope the journal paper to RQ1–RQ3 below. The digital-twin and next-step prediction work becomes a separate follow-up paper (or a short appendix), because its current evidence is the weakest and it dilutes the claim.

**Core claim:** In transactional review workflows, case-centric flattenings do not merely lose relations; they make some cross-object risk predicates *uncomputable* and others *silently wrong*. An executable, predicate-level measure (COOC) quantifies this, and the effect shows up on real public event data, not only on our synthetic benchmark.

**Contributions (final wording to be fixed after results):**
1. A **predicate-family taxonomy** for review lifecycles (stage order, retry limits, actor conflict, capacity/load, version lineage, finality/immutability, concurrent duplicates, stall/deadlock) with an executable OCEL oracle and per-representation computability/correctness tests.
2. **COOC** and a companion **silent-error rate**, with bootstrap CIs and predicate-set sensitivity.
3. An **empirical study on ≥ 6 public real/simulated OCEL or event sources** from four domains (code review, peer review, legislative procedure, education), plus the capstone synthetic benchmark.
4. A **capstone OCEL schema, rule set and leakage-free benchmark generator** (released with oracle labels).
5. A candid **relational-source baseline** (query the source tables directly) so the paper says what OCEL adds beyond SQL.

**Closest prior art to cite and differentiate (all found 2026-10-27; verify each before citing):**
- Miri, Khayatbashi, Zdravkovic, Jalali (2026), *Decision Analytics Journal* 19:100724 — Moodle→OCEL, direct educational prior art. Related: PM4Moodle demo (CEUR-WS Vol-4274, paper 34); OCPM² (arXiv:2503.10735, LMS + administrative grading data); Khayatbashi, Miri, Jalali (arXiv:2412.00393, four-year BPM course log, drill-down/roll-up operations).
- Adams, Park, van der Aalst (2023) — flattening as information loss for predictive monitoring; and the feature-extraction framework paper (arXiv:2209.01219). *They measure ML-feature loss, not predicate-level correctness.* This is the key novelty boundary for COOC.
- van der Aalst (2019) — deficiency/convergence/divergence; Adams & van der Aalst on connected-component case extraction (vdaalst.com/publications/p1412.pdf) — our strongest flattening baseline.
- Küsters & van der Aalst, OCPQ (arXiv:2506.11541) and Li/Park/van der Aalst object-centric constraint checking; `ocpa` constraint monitoring — existing ways to *express* cross-object constraints. We do not claim to invent object-centric constraints.
- Premchaiswadi & Porouhan (2015), process modelling and bottleneck mining in online peer-review systems (PMC4546073) — closest prior process-mining study of a review workflow.

**Risk to the novelty claim:** Adams/Park/vdA may already cover the "flattening loses information" message. Our delta must be the *predicate-level, oracle-checked, silent-error* framing and the review-lifecycle domain. If a literature re-check in Week 1 finds a direct predicate-level precedent, pivot to the domain/schema/benchmark contribution.

---

## 4. Research questions, hypotheses, and preregistration

| RQ | Hypothesis (falsifiable) | Primary test |
|---|---|---|
| **RQ1** Which predicates survive flattening? | **H1:** COOC(OCEL) > COOC(c) for every case notion *c* on every dataset where the data has ≥ 2 many-to-many object relations. If not, report which dataset/predicate is the exception. | Paired per-predicate comparison, Holm-corrected; bootstrap 95 % CI over scope units (projects/changes/papers). |
| **RQ1b** Does flattening fail loudly or silently? | **H2:** The silent-error rate (computable but wrong) is > 0 for ≥ 1 predicate family in every flattening, and rises with the measured convergence/divergence index. | Spearman ρ between per-dataset convergence+divergence index and silent-error rate. |
| **RQ2** Does native OCEL beat the *relational source*? | **H3 (exploratory, may be null):** OCEL matches but does not exceed direct SQL on the source tables for predicate *correctness*; the OCEL advantage is portability and tool support. | Same predicates run as SQL over the source schema. A null result is publishable and strengthens credibility. |
| **RQ3** Do documentation-style rules find real deviations? | **H4:** Rules written from the workflow's state machine flag deviations in real review logs at a rate that independent human labels confirm (precision ≥ 0.8 on a stratified sample, κ ≥ 0.6 between two raters). | Stratified sample of 200 flagged + 200 unflagged cases, two blind raters, Cohen's κ, adjudication log. |
| **RQ4** Is COOC stable? | **H5:** Rankings of representations are unchanged under predicate leave-one-out, 0–40 % link missingness, and 0.5–20 % anomaly prevalence. | 30 seeds × cohort sizes {60, 120, 500, 2000} × missingness sweep on the synthetic benchmark. |

**Preregistration (do this *before* running Phase 4):** freeze on OSF (or the repo with a signed git tag): predicate definitions in executable form, flattening procedures, thresholds (τ for "correct"), datasets and filters, sampling protocol, and primary tests. Write the tag name into the paper. This fixes A6.

---

## 5. Data-source plan

### 5.1 Finding: no public capstone-portal logs exist

Searches (Zenodo, 4TU, Kaggle/Figshare phrasing, OCEL site, general web) found no public event log of capstone, thesis-supervision, or final-year-project management. The closest public education logs are LMS clickstreams (Moodle, OULAD). So the plan uses **structurally analogous public workflows** and states that limitation in the paper. Real portal logs stay as a clearly separated future-work path (§9).

### 5.2 Source catalog

"Verified" = metadata read via Zenodo API / site on 2026-10-27. Sizes are those files only.

| ID | Source | Why it is useful | Access / licence | Files & size | Role |
|---|---|---|---|---|---|
| **S0** | Own synthetic capstone benchmark (`synthetic/`) | Only source with the full capstone schema and oracle labels | Own | repo | **Removed 2026-10-27 (§14)**; was: controlled benchmark after fixing A1–A7 |
| **T1-a** | Berti simulated OCEL 2.0: **Hiring**, Hospital, O2C, P2P — Zenodo 13879980 (verified; simulated) | Hiring = staged evaluation with candidates/applications/interviews; others give a classic ERP baseline | CC BY 4.0 | `03_hiring.xml` 6.0 MB; `04_hospital.xml` 4.4 MB; `01_o2c.xml` 10.5 MB; `02_p2p.xml` 4.7 MB | Domain-diversity baselines (simulated) |
| **T1-b** | Order Management — Zenodo 8337464 (verified; simulated, CPN Tools) | Reference OCEL 2.0 SQLite with qualifiers and dynamic attributes | CC BY 4.0 | `order-management.sqlite` 9.6 MB | Format/tool validation |
| **T1-c** | Container Logistics — Zenodo 8428084 (verified; simulated) | Many-to-many (orders, documents, containers) — stress test for convergence | CC BY 4.0 | `ContainerLogistics.sqlite` 16.1 MB | Convergence stress test |
| **T1-d** | P2P — Zenodo 8412920 (verified; simulated, SAP-style) | Approval-before-action rules similar to stage order / actor conflict | CC BY 4.0 | `ocel2-p2p.sqlite` 13.8 MB | Approval/actor-conflict predicates |
| **T1-e** | Angular GitHub commits — Zenodo 8430332 (verified; **real**) | Real data; only file+branch objects, so a low-richness control | CC BY 4.0 | `.jsonocel` 90.1 MB (XML 178 MB, CSV 57.9 MB) | Real-data control; expect small COOC gap |
| **T1-f** | German Bundestag legislative procedures — Zenodo 16811928 (verified; **real**, from the DIP API) | Multi-stage procedure with persons, committees, documents; many-to-many; closest real analogue of staged approval | CC BY 4.0 (check DIP terms too) | main OCEL JSON 268.7 MB; filtered 171.7 MB; XES 100.7 MB | Real staged-approval workflow (Phase 2) |
| **T1-g** | Berti 2026 collection — Zenodo 18333978 (verified) | Recruiting, GitHub-pm4py, Windows events, transfer order | CC BY 4.0 | seven zips, 0.03–2.9 MB | Cheap extra domains |
| **T1-h** | OCEL of publications by W. van der Aalst — Zenodo 17769774 (verified) | Real author/paper/venue relations | **Licence field empty — do not reuse until clarified** | 8.5 MB | Optional |
| **T2-a** | **OULAD** (Open University Learning Analytics Dataset) | Real education data: students, modules/presentations, assessments (scores, submission dates), VLE interactions; 32,593 students, 22 presentations, ~10.7 M VLE rows (per Kuzilek et al. 2017) | CC BY 4.0 (per the paper and UCI listing); official page redirects to `research.stem.open.ac.uk/ouanalyse/`; **file size not yet verified** | CSV tables | Educational multi-entity log → OCEL |
| **T2-b** | Moodle event log, Univ. de Cádiz — Zenodo 21410580 (verified, published 2026-07-17) | Real Moodle activity | CC BY 4.0 | `dataset-anon.csv` 9.5 MB + mapping JSON | Single-notion control (only anonymised learner + activity + time, so it cannot test multi-object loss; likely descriptive context only) |
| **T2-c** | PM4Moodle / Stockholm BPM-course log (Miri et al.) | The exact prior-art dataset | **Not found public** — ask the authors; do not scrape | — | Optional comparison if shared |
| **T3-a** | **CROP** — Gerrit code reviews, Zenodo 3599150 (verified) | A real submit→review→reject→resubmit→accept lifecycle: changes, revisions, reviewers, votes. 11 systems, 50,959 reviews, 144,906 revisions (per project site). Maps well to R1/R2/R3 attempts, reviewer load, self-approval | CC BY 4.0 | `metadata.zip` 14.3 MB; `discussion.zip` 117.2 MB. **Skip `git_repos.zip` (3.5 GB).** Must confirm the vote/label fields exist in the CSVs before relying on them | Main review-lifecycle analogue |
| **T3-b** | **OpenReview via SNOR v1** — Zenodo 15866613 (verified) | Peer-review lifecycle: submissions, reviewers, scores, decisions. 38,262 records, 462,995 comments | CC BY 4.0 | `normalized_papers.jsonl` 448 MB; `normalized_comments.jsonl` 1.28 GB | **Caveat:** the documented comment schema shows no timestamps, so event ordering may be impossible; likely requires the OpenReview public API for timestamps on a bounded set (e.g. one venue-year) after checking OpenReview's terms. Defer. |
| **T3-c** | GH Archive pull-request review events | Real approvals / changes-requested with timestamps | Public hourly files; **licence/terms unverified**. One hourly file is ~132 MB (checked 2024-03-05-15) | per hour | Optional (Phase 2). Needs identity pseudonymisation. |

### 5.3 Predicate-family → dataset mapping (the bridge between capstone and public data)

| Capstone predicate (current) | Generic family | Public-data instantiation |
|---|---|---|
| G5 stage stall | Stall / no progress after stage *k* | Gerrit change idle > N days; Bundestag procedure stuck between readings; Hiring application without next step |
| G9 attempts exhausted | Retry limit reached with no exit | Gerrit change with ≥ k revisions then abandoned; OpenReview submission with max revisions |
| E5 capacity overrun | Resource load above limit | Reviewer with > k open changes (Gerrit); recruiter/interviewer load (Hiring); committee load (Bundestag) |
| E10 duplicate verification | Concurrent duplicate action | Two reviewers start/verdict on the same revision within Δt |
| E12 null/locked score | Finality / immutability | Vote changed after merge; score missing but decision recorded |
| E15 counter skew | Cross-source inconsistency | Revision count in change metadata ≠ number of revision events |
| (not yet modelled) E14 self-approval | Actor conflict | Change owner = approving reviewer (Gerrit); same person proposes and approves (P2P) |
| (not yet modelled) stage order | Stage-order violation | Merge before required approval; payment before goods receipt (P2P) |

Each predicate must be written once as an executable query over native OCEL (the **oracle**), then re-evaluated on each flattening and on the relational source.

### 5.4 Download phases (nothing is downloaded until approved)

- **Phase 1 (≈ 300 MB + OULAD):** T1-a, T1-b, T1-c, T1-d, T1-e (`.jsonocel`), T1-g, T2-a, T2-b, T3-a (`metadata.zip` + `discussion.zip`). Enough for the full pipeline and the main RQ1/RQ2 results.
- **Phase 2 (≈ 0.3–1 GB):** T1-f Bundestag (filtered JSON first); T3-c one or two GH Archive hours or a few repos via the GitHub API.
- **Phase 3 (only if needed):** OpenReview API pull for one venue-year; SNOR files; T1-h after licence clarification.

### 5.5 Data-handling rules
- Raw files live in `realdata/raw/<source>/`, **git-ignored**, each in its own directory with a `SOURCE.md` (URL, DOI, licence, retrieval date, SHA-256).
- Never run scripts from inside a downloaded directory; load files with `python3 -I`. Treat all downloads as untrusted input (no `pickle`, no notebooks executed).
- Pseudonymise GitHub/Gerrit/OpenReview identities (salted hash, salt not published). Publish only derived aggregates plus the generator/loaders, not raw redistributions.
- Record each licence in `realdata/sources.yaml`; cite every dataset with its DOI.
- Public data has no human subjects directly, but ask the guide whether the institution wants a short ethics note for reuse of identifiable public review data.

---

## 6. Experimental design

**E0 — Repair the synthetic benchmark (Weeks 1–2).**
- Implement COOC as code: each predicate declares its required object types / relations / attributes; `computable()` is automatic, `correct()` compares to the OCEL oracle.
- Build real flattenings (project, student, report-version, plus a connected-components case extraction) with pm4py or ocpa; record duplicated events (convergence), repeated activities per case (divergence), orphaned events (deficiency).
- Remove label leakage: detector reads only OCEL tables and object attributes that the production audit trail would actually contain; ground-truth flags live only in `anomaly_ground_truth.csv`.
- Inject all ten documented anomaly types; add E14 self-approval and stage-order predicates.
- Chronological splits; 30 seeds; cohort sizes {60, 120, 500, 2000}; link-missingness {0, 10, 20, 40 %}; anomaly prevalence {0.5, 2, 5, 10, 20 %}.

**E1 — Observability on public data (Weeks 3–5).** Convert each dataset to OCEL 2.0 SQLite (or load as is), instantiate the predicate families, run oracle vs flattenings vs relational source, report COOC and silent-error rate with CIs.

**E2 — Distortion vs observability (Week 5).** Compute convergence/divergence/deficiency statistics per dataset and flattening; relate to silent-error rate.

**E3 — Rule validation with independent labels (Weeks 5–7).** Run rule-based detection on CROP (and Bundestag/OULAD where applicable); sample, label blind by two team members, compute κ and precision with Wilson CIs; report disagreements and what the rules miss.

**E4 — Robustness (Week 6).** Leave-one-predicate-out, missingness and prevalence sweeps; report rank stability.

**E5 — Optional/appendix.** Calibrated policy what-if using rates estimated from CROP (rejection rate, revisions-to-accept, abandon rate) with bootstrap parameter uncertainty; chronological next-step baseline on CROP/Bundestag comparing object-aware vs flat features. Include only if E1–E4 are on schedule.

**Statistics:** bootstrap (≥ 2,000 resamples) over scope units; Wilson intervals for proportions; McNemar for paired correctness; Holm correction across the primary tests; Cohen's κ for raters; all seeds and configs saved to `results/*.json`.

**Reproducibility:** one `make study` target; pinned `requirements.txt`; seeds in config; SHA-256 of every input; results regenerate byte-stable (or document tolerance).

---

## 7. Tooling

- Currently available on this machine: Python 3.14.8, numpy, matplotlib, curl, node. **Not installed:** pandas, scipy, pm4py, ocpa, duckdb, pandoc, LibreOffice.
- Proposal: a project venv with `pm4py`, `pandas`, `scipy`, `duckdb`, `pyyaml`. Risk: pm4py may not support Python 3.14 yet; fall back to a Python 3.12 venv if needed.
- LaTeX (Elsevier `elsarticle` or the target journal's class) for the manuscript; TeX is not installed locally — verify before Week 9.

---

## 8. Manuscript skeleton and venues

1. Introduction (problem, gap, contributions) · 2. Background and related work (OCEL 2.0, flattening, OC constraints, educational process mining, peer-review process mining) · 3. Capstone lifecycle and OCEL schema · 4. Predicate families and COOC (definitions, computability vs correctness, silent error) · 5. Study design (datasets, flattenings, baselines, preregistration) · 6. Results (E0–E4) · 7. Discussion (what OCEL adds beyond SQL; capstone implications) · 8. Threats to validity (analogue-domain transfer, rule circularity, predicate selection, identity linkage) · 9. Conclusion and real-portal validation path · Appendices (schema, predicate SQL, data dictionary, labelling protocol).

Figures: representation × predicate-family heat-map; COOC with CI per dataset; silent-error vs convergence scatter; robustness curves; lifecycle schema diagram. Tables: dataset catalog; predicate definitions; results.

**Candidate venues (scope, deadlines, fees and review times NOT yet checked — verify before choosing):** *Information Systems*; *Decision Support Systems*; *Software and Systems Modeling*; *Journal of Intelligent Information Systems*; *IEEE Transactions on Learning Technologies*; *Computers & Education: Artificial Intelligence*; *Journal of Educational Data Mining*; *Decision Analytics Journal* (where Miri et al. appeared). An ICPM/BPM-workshop version first is a possible stepping stone but is not required.

---

## 9. What this paper still cannot claim, and the real-data path

Cannot claim: real capstone defect rates, detector accuracy on the real portal, causal effect of any policy, generality beyond the studied workflow families. These stay in "Threats to validity" and "Future work". If the institution later releases de-identified `AuditLog` extracts, the same pipeline reruns unchanged (extract → pseudonymise → OCEL → predicates), giving a direct synthetic-vs-real comparison and a stronger follow-up paper.

---

## 10. Timeline (from 2026-10-27; assumes ~15 h/week across three people)

| Weeks | Milestone | Gate |
|---|---|---|
| 1 | Lock scope and journal target; re-check prior art; set up venv; approve Phase 1 downloads; start `realdata/` skeleton | Novelty re-check does not find a predicate-level precedent |
| 2 | E0: executable COOC, real flattenings, leakage-free generator, 10 anomaly types | Unit tests pass; seeds reproduce |
| 3 | **Freeze and tag the preregistration** | Tag exists before any E1 run |
| 3–5 | Loaders → OCEL for Phase 1 sources; E1, E2 | Per-dataset COOC with CIs |
| 5–7 | E3 labelling; Phase 2 downloads (Bundestag, optional GH) | κ ≥ 0.6 or protocol revised and documented |
| 6 | E4 robustness | Rank stability reported |
| 7–8 | Figures, tables, results freeze | Every number traces to a results file |
| 8–10 | Manuscript draft; internal review by guide | Guide sign-off |
| 11–12 | Revise, format for journal, cover letter, data/code release (Zenodo DOI) | Submission |

---

## 11. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Predicate-level precedent exists | Medium | High | Week-1 re-check; fall back to domain/schema/benchmark contribution |
| Public datasets lack fields for some predicates | High | Medium | Declare "not instantiable" per dataset; COOC computed only over instantiable predicates; report coverage of the predicate set |
| Analogue domains judged unrelated to capstones | Medium | High | Explicit family mapping (§5.3), frame as workflow-family study, state the transfer limit |
| Rule/label circularity again | Medium | High | Independent human labels (E3); rules written before inspecting data; frozen preregistration |
| OCEL not better than SQL on source tables (H3) | Medium | Low | Report as a finding; shift emphasis to portability and cross-object tooling |
| pm4py/ocpa incompatibility with Python 3.14 | Medium | Low | 3.12 venv |
| Licence/terms issues (Bundestag DIP, OpenReview, GH Archive, empty licence on T1-h) | Medium | Medium | Verify terms before download; use only CC BY sources in Phase 1; no scraping behind login |
| Time (course load) | High | Medium | One-claim paper; E5 and OpenReview are optional |

---

## 12. Decisions needed from the team

1. Approve the **Phase 1 downloads** (§5.4).
2. Approve creating a **project venv** and installing the Python packages in §7.
3. Confirm the **paper framing**: cross-domain observability study (recommended) vs capstone-only domain paper vs wait for real portal logs.
4. Pick a **target journal** (and whether to use a conference as a stepping stone).
5. Confirm whether the team has any realistic route to **institutional logs** within this timeline.
6. Decide what to do about the **uncommitted disclaimer/docstring edits** (A8).

---

## 13. Execution log and preliminary findings (2026-10-27)

### 13.1 What was done
- Downloaded and MD5/size-verified (CC BY 4.0, ~350 MB): Berti simulated logs (Hiring, Hospital, O2C, P2P), Order Management, Container Logistics, Park P2P, Angular commits, the small Berti collection zips, CROP (`metadata.zip`, `discussion.zip`), the Cádiz Moodle CSV, and OULAD (UCI mirror; the official Open University link returned HTTP 404).
- Built `realdata/`: loaders, flattening statistics, an executable COOC engine with three representation tiers (native oracle, plain flat, denormalised flat) plus a leading-type baseline, 8 predicate templates, a registry of 45 predicates (41 evaluated), violation injection, bootstrap aggregation, a 10-seed run, and an independent SQL cross-check.
- Converted two **real** corpora to OCEL 2.0: CROP (54,487 Gerrit changes, 352,057 events, 11 projects) and OULAD (216,532 events, 32,587 enrolments).
- Wrote `docs/research/Journal_Manuscript_Draft.md` (v0.1) with these numbers. Not run: the rebuild of the synthetic capstone benchmark (audit items A1–A7), human labelling, missingness sweeps, Bundestag, OpenReview.

### 13.2 What the evidence says
| Plan item | Result | Consequence |
|---|---|---|
| H1: native > flat | Supported but largely structural. One plain flat log answers 12.0 % (CI 6.0–18.9) of 41 predicates; one log per object type 70.7 % (56.1–82.9). | Keep, but present COOC as a diagnostic for a stated agenda, not as an empirical law. |
| H2: flattening fails silently | **Not supported.** 0/29 plain and 1/72 denormalised answered pairs were wrong. | Drop "silently wrong" as the headline. |
| New finding | A denormalised export that keeps related object IDs as columns recovers capacity and actor-conflict rules (single log 28.4 %, portfolio 87.8 %). o2o-consistency and object-attribute deadline rules stay unanswerable in every flat tier. Whether the actor is an event attribute or only an object changes the answer for the *same* rule. | **New central message:** what must a flat export carry to answer a given agenda, and what is still unreachable. This also operationalises the plan's "source instrumentation vs representation preservation" split. |
| H3: OCEL vs SQL on source | Cannot be tested on public OCEL files (they are already the relational export). | Test only on the rebuilt capstone synthetic source. |
| Stability | Headline shares identical across 10 injection seeds (SD ≤ 0.002). | Confirms the measure is structural; sampling noise is not the issue, predicate selection is. |
| Real data (descriptive, unvalidated) | CROP: 35.1 % of changes have a person who both uploaded and approved; 1.0 % merged without prior approval; 0.8 % exceed 3 request-changes rounds. OULAD: 47.1 % of enrolments have ≥ 1 late submission. | Needs two-rater labels before any claim that these are violations. |
| Flattening distortion on real OCEL (Angular) | Branch-case flat log is 81.6× the event rows (99.99 % convergence). | Usable as a motivating figure. |

### 13.3 Data-source changes versus §5
- **CROP:** the CSV metadata has no timestamps or reviewers; the `discussion.zip` text does, so the OCEL is built from it (names already pseudonymised by CROP, hashed again). Vote labels are parsed with regexes; validate the parser on a hand-checked sample.
- **SNOR/OpenReview:** documented comment schema has no timestamps → still deferred.
- **Cádiz Moodle CSV:** one flat case notion only; downloaded but not used for multi-object tests.
- **Bundestag, GH Archive, publications OCEL:** not downloaded yet (Phase 2/3).

### 13.4 Deviations from the intended protocol (disclose in the paper)
1. Predicates were written after viewing dataset vocabularies, not blind.
2. After the first run, two rules that were violated by ~100 % of units (HIR-3, O2C-6) were removed, and the LOAD threshold changed from the 75th percentile to the median because ties left < 5 positives.
3. 21 of 41 evaluated predicates use injected violations; 6 of 8 datasets are simulated.
4. The registry has **not** been frozen or tagged yet.

### 13.5 Revised priorities
1. **Team action:** freeze the registry (git tag) before any further run; decide the release licence (`pm4py` is AGPL-3.0).
2. ~~Rebuild the synthetic capstone benchmark~~ — **cancelled by the team on 2026-10-27**; H3 (OCEL vs SQL on a source schema) is therefore dropped (§14).
3. **Team action:** two independent raters label ~200 flagged + 200 unflagged CROP changes and OULAD enrolments; report Cohen's κ.
4. Link-missingness and prevalence sweeps; leave-one-predicate-out.
5. Add Bundestag procedures as a staged-approval dataset; register its predicates first.
6. Figures, prior-art re-check (Adams/Park/vdA, OCPQ), venue choice.
7. Re-scope the manuscript title/abstract around "what a flat export must carry" rather than "flattening fails silently".

---

## 14. Scope change: synthetic benchmark and demo removed (2026-10-27)

The team decided to base the paper on real data only. `synthetic/` (generator, three scenario datasets, Review 2 analysis outputs) and `demo/` (Review 2 frontend) were deleted from the working tree. Both remain in Git history (last commit that contains them: `28b629c`; restore with `git checkout 28b629c -- synthetic demo`). Uncommitted edits they carried were saved to a scratchpad patch and are not part of the repository.

Consequences for this plan:
- **Audit items A1–A8** concerned the deleted code and no longer need fixing. They remain useful as a record of why the Review 2 synthetic numbers (e.g. macro-F1 0.977, deadlock 11.2 % → 1.3 %) must not be cited in the journal paper.
- **H3** (does OCEL beat SQL on the source schema) is dropped: it could only be tested on a source schema we controlled.
- **No capstone-shaped data remains in the study.** The capstone relevance of the paper now rests on (a) the documented platform lifecycle in `docs/educational-capstone-platform/`, (b) CROP/Gerrit as the closest public review-lifecycle analogue, and (c) a clearly stated future-work path to de-identified portal logs. State this limitation plainly; a reviewer will ask why a capstone paper contains no capstone data.
- **Review 2 deliverables** (`docs/review-2/*.pptx`, `*.docx`, `docs/research/Team1_Literature_Review.docx`) still describe the synthetic results and were not edited. Keep them as course artifacts and do not reuse their numbers.
- Repository plumbing updated accordingly: `README.md`, `Makefile`, `scripts/check_package.py`, `.github/workflows/validate.yml`, `.gitignore`, `CITATION.cff`, `SECURITY.md`, `PUBLICATION_CHECKLIST.md`.
