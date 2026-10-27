# Novelty assessment and re-scope (2026-10-27)

**Decision inputs from the team:** no capstone data (none exists); **no synthetic or simulated data**; if novelty is weak, find new ways to study the data, more real data, or better metrics.
**Method:** web/Crossref/arXiv/Semantic Scholar searches on 2026-10-27, summaries of search results, plus abstracts where retrievable. Full texts of the closest papers were **not** read (arXiv rate-limited the session), so every "not found" below means "not found by these searches", not "does not exist". A final check in Scopus / Google Scholar by the team is required before any novelty claim is written into a submission.

## 1. Verdict on the contributions we had

| Claim | Verdict | Why |
|---|---|---|
| Flattening loses information / distorts (deficiency, convergence, divergence) | **Not novel** | Defined and analysed by van der Aalst (2019); formal remedy by Adams & van der Aalst (2024); ML-feature and graph-structure loss by Adams, Park, van der Aalst (2023) and Adams et al. (2022); spurious directly-follows relations by Waibel et al. (2022); OC data-quality catalogues by Kabierski et al. (2026) and Sadeghianasl et al. (2026). |
| COOC: predicate-level observability coverage with a silent-error split | **Weak** | (1) Value is mostly determined by which fields a representation contains, i.e. by the author-chosen predicate set; (2) the one empirical hypothesis (silent errors) came out null (0/29 and 1/72); (3) with real data only, 11 predicates over 2 logs remain, too few for any statistic. No direct predecessor was found, but there is also little to publish. |
| Capstone-specific OCEL schema and rules | **Cannot be evaluated** | No capstone data exists; the schema is documentation-derived only. |
| Review-lifecycle findings on Gerrit (self-approval, merges without approval, rework) | **Descriptive only** | Self-merge and review-bypass rates are known practitioner metrics (CHAOSS, Chromium audit); MSR studies of Gerrit are extensive. No object-centric/conformance study of Gerrit logs was found (GitHub-to-OCEL tooling exists), so the OCEL angle is new but modest. |
| OULAD as an object-centric log | **New application, modest** | No OCEL + OULAD paper found; OULAD prediction literature is saturated, so a prediction contest would not be novel. |

## 2. The gap that survived the search

> No study was found that **measures, across several real-life object-centric logs, how often and how severely flattening distorts what analysts compute** (event-count inflation, false adjacency between unrelated sub-objects, cross-case coupling), or that reports how much of this appears in real data versus the simulated logs that dominate the OCPM literature.

Evidence that this is a gap: the flattening problems are illustrated with toy or single-case-study examples (Waibel et al. food-production case; an IBM-related paper's illustrative count inflation); the official OCEL collection is mostly simulated (we counted the real ones: Angular, German Bundestag, Enron, Ethereum, Age of Empires, publications); the OCED quality papers classify issues, they do not report distortion rates.

Related prior art for the coupling idea: inter-case features in predictive monitoring (Senderovich et al., 2017, doi:10.1007/978-3-319-65000-5_18; 2019, doi:10.1016/j.is.2019.01.007), so "cross-case effects matter" is established; what is open is measuring cross-case *coupling structure* from OCEL across real logs.

## 3. What we learned this session (real data only, no injection)

**Real-only COOC.** 11 predicates, 2 logs (CROP, OULAD): one plain flat log answers 17 % (CI 0–41), one denormalised log 64 % (CI 36–86); 0 silent errors in 34 answered pairs. Too few predicates for inference. COOC stays as an appendix at most.

**Predicate-free distortion metrics** (`realdata/src/distortion.py`; per case notion in `realdata/results/distortion/*.json` and `distortion_summary.md`; per log in `log_level_summary.csv`). Seven real logs, no simulation, no injection. "Case notions" are the object types (Enron split by role, e.g. sender vs recipient); only case notions covering at least 1,000 events are summarised.

| Real log | Events | Types | Objects/event | Max event duplication when flattening (copies/event) | Median deficiency (events dropped) | Type pairs with ≥ 50 % shared objects |
|---|---:|---:|---:|---:|---:|---:|
| Angular commits | 27,842 | 2 | 88.0 | **81.7×** (branch case); 6.5× (file case) | 0.00 | 2 of 2 |
| Enron e-mail (100k mails) | 96,175 | 4 | 3.5 | **2.11×** (CC role), 1.57× (TO role), 1.00× (sender role) | 0.23 | 8 of 12 |
| Age of Empires (10 matches) | 34,860 | 25 | 4.3 | 1.76× | 0.86 | 50 of 137 |
| German Bundestag (20th period) | 62,719 | 44 | 1.06 | 1.28× | 0.91 | 2 of 13 |
| Ethereum DApps (300k-event window of 3.2 M) | 300,000 | 5 | 1.6 | 1.09× | 0.69 | 10 of 20 |
| CROP / Gerrit (11 projects) | 306,716 | 3 | 3.0 | 1.00× | 0.00 | 4 of 6 |
| OULAD | 216,532 | 4 | 3.8 | 1.00× | 0.00 | 7 of 12 |

What the seven logs show (descriptive, n = 7):
1. **Event duplication from flattening is usually small.** Four of seven logs have at least one case notion with more than 5 % duplicated events, but only Angular (fan-out of files per commit) is extreme. Median duplication is 1.0–1.3× outside Angular.
2. **Deficiency, not duplication, dominates in logs partitioned by object kind** (Bundestag procedure types, Age of Empires unit types, Ethereum): a single case notion drops 69–91 % of events at the median, so an analyst must union many per-type logs or lose most of the process.
3. **Cross-case coupling is everywhere**: in every log, many type pairs share more than half of their objects across cases (people across changes, students across assessments, accounts across markets), so the case-independence assumption of a flat log is violated even when no event is duplicated.
4. **Three structural regimes** emerge: *star* logs (CROP, OULAD: one object per type per event; no duplication), *partitioned* logs (Bundestag, Age of Empires, Ethereum: high deficiency), *fan-out* logs (Angular, Enron: real duplication). Which regime a log is in is readable from the object graph before any analysis.

Limits: seven logs from five domains; Ethereum is a contiguous window of the real log; case-notion choices are by object type (and role for Enron); "nested child" detection and adjacency metrics are only informative for CROP, OULAD, Ethereum, and a few Bundestag types; Enron has 72 events (0.1 %) with timestamps before 1990 and a range ending in 2020, a data-quality flag for a 1998-2002 corpus.

**Consequence analysis** (`realdata/src/consequence.py`; self-checked against a plain-Python implementation by `check_consequence.py`; tables in `results/consequence_by_log.md` and `consequence_by_notion.csv`). Reference = what the object-centric log says exactly: each distinct event once, and each distinct pair of consecutive events in the lifecycle of at least one object. 38 case notions over the seven real logs; all comparisons use real data only.

| Standard output | What was compared | Result across 38 case notions |
|---|---|---|
| Activity-frequency ranking | flat(T) row counts vs distinct events | **Duplication alone** barely reorders it: Spearman ρ < 0.95 in only 2 notions (Angular files 0.81, Enron recipients 0.93). **Narrowing is the real effect:** in 20 of 38 notions the flat log shows fewer than half of the process's activities, and in 19 the ranking correlates below 0.5 with the whole process (Bundestag, Age of Empires, Ethereum; minimum ρ ≈ 0). |
| Directly-follows frequencies | edge counts with vs without duplicated pairs | Pair duplication up to 74× (Angular branch case), 1.7× (Age of Empires), 1.6× (Enron); the rank order of edge frequencies stays ρ ≥ 0.94 except Age of Empires villagers (0.88). |
| Spurious directly-follows edges | edge types that occur in a parent flat log but never inside any nested child's lifecycle (adjacent events fully inside the children's coverage) | 5 % (CROP project case), 17 % (OULAD presentation case), 24-28 % (Age of Empires player/session), 2 % (Ethereum, Bundestag). |
| Entity rankings from a denormalised flat export | ρ between true events per entity and the row count the export gives, visible entities only | Median ρ 0.90 (Enron), 0.78 (Ethereum), 0.57 (Bundestag); **worst cases 0.16 (Enron), -0.01 (Ethereum), -0.41 (Age of Empires)**; CROP and OULAD are exactly 1.00 because no event has several objects of a type. |
| Variant counts | variants per case and top-10 coverage, parent vs nested child | **No systematic direction.** Variants per case ranges from 0.0003 to 1.0 depending on the case notion; parent notions often have too few cases to compare (10-22), and in Bundestag the child is more variable than the parent. I am not claiming that flat parents hide standard paths. |

How to read it: flattening rarely corrupts a ranking by duplication, except in fan-out logs. The dominant consequence is **narrowing**: one case notion shows a small, differently-ranked slice of a partitioned log. That is intuitive, so the paper's contribution would be the quantification and the regime taxonomy, not a surprising mechanism. Entity rankings built naively from a denormalised export are the one place where a careful-looking output can be badly wrong (Enron, Ethereum, Age of Empires); an analyst who de-duplicates by event id would avoid it, so this is a risk of careless counting, not an inherent loss.

**Exploratory (not a finding):** reviewer workload vs first-response latency in CROP. Pooled Spearman ρ = 0.108, but within project-quarter strata the weighted ρ = −0.009 (cluster-bootstrap CI −0.051 to 0.040): the pooled association is confounding by project and period, and no capacity effect is detectable with this proxy. This is a useful warning for any cross-case claim.

## 4. Candidate directions (ranked)

| # | Direction | Novelty | Data needed | Main risk |
|---|---|---|---|---|
| **A** | **"When does object-centricity matter in real data?"** Predicate-free distortion and coupling metrics (copies per event, activity-frequency inflation, nested-child adjacency, object-level coupling) over 8–9 real logs; plus a downstream-consequence check where outcomes exist (e.g. do coupling features change an analysis result). | Medium; fills the confirmed gap | 5–6 more real many-to-many logs | Result may be "rarely, except M:N logs"; still publishable as a nuanced empirical finding if the logs are diverse. |
| B | Application/dataset paper: first OCEL conversions of Gerrit (CROP) and OULAD with converters, validation, and object-centric analyses (reviewer networks, rework, deadline congestion). | Low–medium | already have | Reads as a data note unless findings are strong. |
| C | Cross-case coupling effects on performance/outcomes with OCEL-defined load. | Low (inter-case features exist) | already have | Exploratory CROP result was null. |
| – | Not recommended: capstone-only paper; hand-picked-predicate COOC as the main contribution; another OULAD prediction benchmark. | – | – | – |

**Recommendation (updated after the consequence analysis):** A is **a modest but real empirical contribution, still thin for a journal on its own**. The honest result is 'duplication rarely matters; narrowing and careless entity counting do', which no prior multi-log study was found to report, but reviewers will call narrowing expected. To reach journal level add at least two of: process-discovery model quality (fitness/precision) from flat vs object-centric discovery on the same logs; a predictive-monitoring comparison with chronological splits; two or three more real logs (BPI 2019 derived to OCEL, a GitHub pull-request sample); a small practitioner check on whether the distortions would change decisions. The earlier assessment was: seven descriptive log profiles and a three-regime taxonomy are an honest, novel-in-its-evidence-base result, but a journal paper also needs a *consequence* analysis showing how much a standard analysis output changes under flattening (for example, ranking of the busiest/bottleneck entities, variant counts, or directly-follows frequencies versus an object-centric computation on the same log), plus two or three more real logs (BPI 2019 derived to OCEL, a GitHub pull-request sample). Without that, fall back to B (conversions + analysis) or position A as a short empirical paper.

## 5. Additional real data (first four rows and the OULAD extract were downloaded on 2026-10-27 and checksum-verified; BPI 2019 is still pending)

| Log | Why | Source | Licence | File(s) |
|---|---|---|---|---|
| German Bundestag procedures (real) | Staged approval lifecycle (readings, committees, persons, documents): closest real analogue of a multi-stage review | Zenodo 16811928 | CC BY 4.0 (also check DIP terms) | `Period20_procedure_steps_all_additional_event_types_filtered.json`, 171.7 MB (full: 268.7 MB) |
| Enron e-mail OCEL (real) | Genuine many-to-many (one e-mail, many recipients); contains personal data, must be pseudonymised | Zenodo 21989732 | CC BY 4.0 | `enron_top_100000.ocel.zip`, 56.1 MB |
| Ethereum DApp execution OCEL (real) | Transactions × accounts × contracts, many-to-many | Zenodo 21989580 | CC BY 4.0 | `ethereum_blockchain.ocel.zip`, 66.8 MB |
| Age of Empires 2 matches (real human play) | Many-to-many between players, units, buildings | Zenodo 13365584 | CC BY 4.0 | `age_of_empires_ocel2_10_match_filter.zip`, 3.8 MB (full SQLite 891.9 MB) |
| BPI Challenge 2019 (real SAP purchase-to-pay; flat XES, OCEL must be derived) | Item-level 1:N structure, resources | 4TU, doi:10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1 | CC BY 4.0 | XES, size to be confirmed at download |
| OULAD `studentVle.csv` (real clicks on VLE sites) | Adds shared VLE-site objects to OULAD; **already inside the downloaded zip, no new download** | UCI mirror of OULAD | CC BY 4.0 | 453.8 MB extracted |

Excluded because they are synthetic or simulated: all Berti/Knopp/Park simulated logs, the "Synthetic relational databases" collection, the hinge-production log, and all violation injection.

## 6. Cleanup already done
Removed from the study: the simulated sources (kept on disk, unused), the violation-injection module and seed script, simulated-derived results, and simulated predicates in the registry. The manuscript draft v0.2 is **superseded**: all its headline numbers came from simulated logs and injected violations and must not be cited.
