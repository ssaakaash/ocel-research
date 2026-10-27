# What Does Flattening Hide? Measuring Case-Notion Distortion and Its Consequences on Seven Real Object-Centric Event Logs

**Status: working draft v0.4 (2026-10-27). Not submitted, and no venue chosen yet.** v0.4 reframes the narrowing result around case notions an analyst would plausibly choose, adds threshold sensitivity, explains how the logs were chosen, and makes the tone more formal. v0.3 replaced v0.2, whose headline results came from simulated logs that the team has since excluded. Every number below comes from `realdata/results` and regenerates with `make study`; the three tables and the narrowing counts are printed by `scripts/review3/make_paper_tables.py`.
**Authors:** Aakaash Sathya Saravanan, Mitisha Sharma, Tanmay Khambete. Guide: Dr. Kalyanaraman P. (author order and affiliations to be confirmed.)
**Data:** seven public logs, all real, all CC BY 4.0. No synthetic or simulated data. No capstone-portal data.

---

## Abstract

Process mining assumes one case per event, but many real workflows give an event several. A code review involves a change, a reviewer and a project, and an e-mail involves a sender, several recipients and a message identifier. The usual remedy is flattening: one object type is chosen as the case notion, and events are copied, dropped or merged until each fits a single case. The literature names the resulting problems (convergence, divergence and deficiency), but we found no study that measures them across several real logs.

We measured them on seven public object-centric logs from code review, education, legislation, e-mail, blockchain, software commits and game play, covering 38 case notions. We then compared four outputs an analyst would read from a flat view (activity rankings, directly-follows edges, process variants and entity rankings) with the same outputs computed on the object-centric log.

The logs fall into three groups. In star logs flattening copies nothing. In partitioned logs a case notion drops 69% to 91% of the events in the median. In fan-out logs events are duplicated, up to 81.65 copies per event. Duplication alone rarely changes a ranking: only 2 of 38 case notions fall below a rank correlation of 0.95 against the same events counted once. The larger effect is narrowing, where a flat log shows under half of the process's activities. It occurs in 20 of 38 case notions, but 18 of these come from two logs in which object types are separate sub-processes. Among the 15 case notions that cover at least half of a log's events, narrowing remains in 2, and in two logs no case notion covers half the events at all. Counting rows in a denormalised flat export can also reverse entity rankings, with worst-case rank correlations of 0.16, -0.01 and -0.41.

All results are recomputed from open code and reproduce byte for byte. Parts of the pipeline are checked against independent SQL, brute-force and raw-file implementations, and a plain-Python re-implementation of the distortion metrics agrees exactly on slices of three logs. These checks found three bugs in our own code. Nobody outside the team has labelled the findings.

**Keywords:** object-centric process mining, OCEL 2.0, event data flattening, convergence and divergence, case notion, educational process mining.

---

## 1. Introduction

Almost every process-mining tool begins by asking for a case identifier. For a purchase order passing through three departments, this works well. It works less well for an e-mail with a sender, five recipients and a message identifier, or for a Gerrit review in which a change, two reviewers and a project all appear in the same event.

The usual answer is flattening. We choose one object type as the case notion and rewrite the log so that each event belongs to one case. Events with several objects of that type are copied, which is convergence. Events with no object of that type are dropped, which is deficiency. Repeated events that belong to different objects of another type are merged into one case, which is divergence [1]. Object-centric event logs avoid this rewrite. In OCEL 2.0 [2] an event can refer to any number of typed objects, and objects can refer to each other.

There is good reason to expect this structure to matter. Keeping the object graph improves machine-learning tasks compared with flattened features [3], and Adams and van der Aalst [4] treat convergence, divergence and deficiency together. One-to-many links produced false directly-follows relations in a food-company case study [5]. Object-centric data also has quality problems of its own [6]. In education, group and resource links stay invisible in a student-centric view of Moodle activity [7].

When we looked for numbers, however, we found few. How often does a flat view copy events? How much does it drop? Does either effect change what an analyst reads from a chart? Our searches of Zenodo, 4TU and the web returned examples and single case studies, but no measurement across several real logs. That is the gap this paper addresses, although we do not claim our search was exhaustive.

We address the gap in a modest way, with three contributions.

1. We compute distortion metrics for 38 case notions on seven real public logs and group the logs into three regimes.
2. We compare four standard outputs (activity rankings, directly-follows edges, variants, entity rankings) between flat and object-centric views. We keep duplication apart from narrowing, because an analyst can undo the first but not the second, and we separate narrowing in case notions an analyst would plausibly choose from narrowing that follows from the structure of the log.
3. We verify parts of the pipeline independently, report the three bugs those checks found in our own code, and make the whole study re-run with one command.

There are three things we explicitly do not claim. We are not the first to use OCEL in education [7]. We say nothing about how real capstone teams behave, because we had no portal data. And seven logs are not enough to establish a general law.

## 2. Background and related work

**The flattening problem.** van der Aalst [1] explains why logs with one case per event misrepresent processes with interacting entities, and Adams and van der Aalst [4] address convergence, deficiency and divergence together. Both contributions are conceptual. Neither reports how often these effects occur in real data.

**The format.** OCEL 2.0 [2] stores events, objects, event-to-object and object-to-object relations, each with qualifiers, in JSON, XML or SQLite. We read all three forms (plus parquet bundles of the same model) and write the SQLite form.

**Consequences and quality.** Waibel et al. [5] used a causal event graph to show spurious directly-follows relations arising from one-to-many links, on data from one company. Kabierski et al. [6] classify quality issues in object-centric data; they describe the kinds of problems but do not count them. Adams et al. [3] show that structure-preserving encodings outperform flattened features on predictive tasks.

**Education and review processes.** Miri et al. [7] applied object-centric mining to Moodle data, which makes them our closest neighbour. Hassani et al. [10] describe a department supervising more than 250 final-year computing projects, without event data, and Premchaiswadi and Porouhan [11] mined an online peer-review process with one case notion. None of these studies measures flattening.

## 3. Method

### 3.1 Logs and case notions

**How the logs were chosen.** The study began from a question about capstone review, and no public capstone or thesis-supervision event log exists. We therefore started with two real logs of related processes, Gerrit code review (CROP [9]) and student enrolment and assessment (OULAD [8]), and converted both to OCEL 2.0 ourselves. To see whether the results depend on the domain, we then searched Zenodo, 4TU and the OCEL website for further logs. We kept a log if it met four conditions: it records real activity, not a simulation; it is openly licensed; its events carry timestamps; and it has at least two object types linked to events. Five logs met these conditions and were added. We excluded all simulated OCEL logs, a Moodle log with only one object type, an OpenReview corpus whose comments carry no timestamps, and a publications log with no stated licence. A further candidate (BPI Challenge 2019) is a flat log from which an OCEL would first have to be derived, and it is not included. The seven logs are therefore a purposive sample chosen for domain variety, not a random sample of object-centric logs.

Table 1 lists the logs. Five already come as OCEL files (Angular and Bundestag as JSON, Age of Empires as SQLite, Enron and Ethereum as parquet bundles). Ethereum has 3.2 million events and does not fit in the 8 GiB of memory available to us, so we use a contiguous window of 300,000. Enron e-mail addresses are split by role (sender, recipient, copied) and hashed. A *case notion* is an object type. We call it *analysed* when its flat log covers at least 1,000 events, which leaves 38.

**Table 1.** The seven logs.

| Log | Domain | Events | Objects | Object types | Objects per event | Analysed case notions |
|---|---|---|---|---|---|---|
| CROP (Gerrit) | code review | 306,716 | 55,323 | 3 | 3.0 | 3 |
| OULAD | education | 216,532 | 61,577 | 4 | 3.8 | 4 |
| German Bundestag | legislation | 62,719 | 37,665 | 44 | 1.1 | 9 |
| Age of Empires II | game play | 34,860 | 5,054 | 25 | 4.3 | 11 |
| Ethereum (window) | blockchain | 300,000 | 17,773 | 5 | 1.6 | 5 |
| Angular commits | software commits | 27,842 | 28,317 | 2 | 88.0 | 2 |
| Enron e-mail | e-mail | 96,175 | 70,541 | 4 | 3.5 | 4 |

### 3.2 Distortion metrics

Let *E* be the events, *O* the objects with types τ(*o*), and *R* ⊆ *E*×*O* the event-to-object relation. For a case notion *T*, let *R_T* be the pairs in *R* whose object has type *T*, and *E_T* the events in them. Flattening on *T* gives one row per pair in *R_T*, which is how pm4py flattens. Then:

- **Deficiency** δ(*T*) = 1 − |*E_T*| / |*E*|, the share of events a flat view drops. Its complement is the *coverage* of *T*.
- **Convergence share** κ(*T*): the share of events in *E_T* with two or more *T*-objects.
- **Copies per event** c(*T*) = |*R_T*| / |*E_T*|. It is 1.0 when nothing is copied.
- **Divergence share**: among pairs of a case and an activity with two or more events, the share whose events differ in the set of objects of at least one other type.
- **Coupling** for an ordered pair of types (*T*, *U*): the share of *U*-objects that take part in events of two or more *T*-objects.

A type *U* is a *nested child* of *T* when 95% or more of its objects occur in one *T*-case, each has its own lifecycle (two or more events), and the fan-out is at least 1.5 per case. These three thresholds and the 1,000-event cut-off are our own choices, fixed at the top of the code, and we did not tune them to improve a result.

### 3.3 Consequence analysis

The reference is the object-centric view. Every event counts once, and the directly-follows relation is the union of consecutive-event pairs over the lifecycle of every object of every type. For each analysed case notion we compare four outputs with this reference.

- **C1, activity ranking.** Spearman's ρ between the flat activity counts and (a) the whole-process counts, and (b) the counts of the same covered events counted once. Measure (b) isolates duplication; measure (a) adds narrowing. We also report the share of activities that are visible at all, and we call a case notion *narrowed* when fewer than half of the process's activities are visible.
- **C2, directly-follows edges.** Duplication of event pairs, rank agreement of edge frequencies with and without duplicates, and, where nested children exist, the share of flat adjacent pairs whose edge type never occurs inside any child (the spurious edge mass).
- **C3, variants.** Distinct activity sequences per case.
- **C4, entity ranking.** For every other type with at least 30 objects, ρ between the true number of events per object and the row count a denormalised flat export of *T* would give, over the objects that appear in the export.

Events are ordered by sorted event identifier so that ties in time always break the same way.

### 3.4 Plausible case notions and sensitivity

Some object types would never be chosen as a case notion. In Age of Empires II, a farm or a house takes part in a handful of activities, and in the Bundestag each object type is a separate kind of parliamentary procedure. Narrowing in such types follows from the structure of the log. To separate it from narrowing an analyst could actually fall into, we report narrowing in two further ways. The *widest* case notion of a log is the one that covers the most events, which is the natural first choice. A case notion is *plausible* when it covers at least half of the log's events. We added both views after seeing the first results, so we report the coverage threshold at 30% to 70%, the narrowing threshold at 0.3 to 0.7, and the 1,000-event cut-off raised to 2,000 and 5,000. The cut-off cannot be lowered without re-running the analysis, because case notions below it were never analysed.

### 3.5 Verification

We checked what we could. Downloads from Zenodo are compared with the published size and MD5, and every file receives a SHA-256 checksum. A brute-force Python version of the directly-follows pairs and of one entity ranking agrees with the vectorised code on a 6,000-event slice of Enron (four case notions). Four rules of an earlier rule engine were re-implemented in SQL and match on CROP, and three counts were recomputed from the raw OULAD files. Re-running the whole study (`make study`, about five minutes on a laptop) leaves every tracked result file byte-identical. These checks found and fixed three bugs: duplicate CROP event rows (about 17%), a missed Gerrit abandon message, and event ordering under timestamp ties. A second implementation of the distortion metrics, written with plain dictionaries and sets and no pandas, agrees exactly with the pandas code on 6,000-event slices of Enron, Bundestag and Age of Empires II (60 case notions and every type pair, divergence and variants included). We have not run that second implementation on the full logs, found an independent labeller, or asked a second team to check the converters.

## 4. Results

### 4.1 Three regimes of distortion

Table 2 and Figure 1 show the distortion per log. The logs fall into three groups.

**Table 2.** Flattening distortion per log, over analysed case notions.

| Log | Regime | Median share of events dropped | Median copies per event | Largest copies per event | Notions with over 5% duplication | Type pairs sharing at least 50% of objects |
|---|---|---|---|---|---|---|
| CROP (Gerrit) | star | 0.0% | 1.00 | 1.00 | 0 of 3 | 4 of 6 |
| OULAD | star | 0.0% | 1.00 | 1.00 | 0 of 4 | 7 of 12 |
| German Bundestag | partitioned | 90.8% | 1.00 | 1.27 | 2 of 9 | 2 of 13 |
| Age of Empires II | partitioned | 86.3% | 1.01 | 1.76 | 4 of 11 | 50 of 137 |
| Ethereum (window) | partitioned | 68.9% | 1.04 | 1.09 | 2 of 5 | 10 of 20 |
| Angular commits | fan-out | 0.1% | 44.06 | 81.65 | 2 of 2 | 2 of 2 |
| Enron e-mail | fan-out | 23.1% | 1.29 | 2.11 | 2 of 4 | 8 of 12 |

*Star logs (CROP, OULAD).* No event involves two objects of the same type. Flattening copies nothing (1.00 copies per event) and, in the median, drops nothing. On these two measures the distortion is zero.

*Partitioned logs (Bundestag, Age of Empires II, Ethereum).* Little is copied, with at most 1.27, 1.76 and 1.09 copies per event. However, different object types cover different parts of the log, so a case notion drops 69% to 91% of the events in the median.

*Fan-out logs (Angular commits, Enron).* One event relates to many objects of the same type. The largest duplication is 81.65 copies per event in Angular (the branch case notion) and 2.11 in Enron.

![Figure 1. Duplication and dropped events for the seven logs. Each dot is one log. The horizontal axis is the largest duplication of any analysed case notion (copies per event, log scale); the vertical axis is the median share of events a case notion drops.](fig_regimes.png)

Coupling cuts across the groups. Apart from the Bundestag (2 of 13 type pairs) and Age of Empires II (50 of 137), at least half of the type pairs have at least half of one type's objects taking part in events of two or more objects of the other, and in Angular both pairs do. The cases of these logs therefore overlap heavily, while a flat view treats them as separate.

### 4.2 Consequences for standard outputs

**Table 3.** Consequences of flattening per log.

| Log | Notions | Activities visible (median) | Activity rank correlation vs whole process (median / lowest) | Lowest, duplication only | Largest edge duplication | Lowest entity-rank correlation |
|---|---|---|---|---|---|---|
| CROP (Gerrit) | 3 | 1.00 | 1.00 / 1.00 | 1.00 | 1.00 | 1.00 |
| OULAD | 4 | 1.00 | 1.00 / 0.87 | 1.00 | 1.00 | 0.98 |
| German Bundestag | 9 | 0.10 | 0.17 / 0.00 | 1.00 | 1.26 | 0.34 |
| Age of Empires II | 11 | 0.12 | 0.21 / -0.05 | 1.00 | 1.69 | -0.41 |
| Ethereum (window) | 5 | 0.79 | 0.64 / 0.02 | 1.00 | 1.02 | -0.01 |
| Angular commits | 2 | 0.98 | 0.88 / 0.81 | 0.81 | 74.05 | 0.88 |
| Enron e-mail | 4 | 1.00 | 0.97 / 0.87 | 0.93 | 1.57 | 0.16 |

**Duplication alone rarely changes a ranking.** When the flat activity ranking is compared with the ranking of the same events counted once, only 2 of the 38 case notions fall below ρ = 0.95: Angular files (0.81) and the Enron "to" role (0.93). In the star logs the correlation is exactly 1.0.

**Narrowing is the larger effect, but much of it is structural.** In 20 of 38 case notions the flat log shows fewer than half of the activities of the whole process. Against the whole process, the median activity-rank correlation is 0.17 in the Bundestag and 0.21 in Age of Empires II. These numbers need care. Eighteen of the 20 narrowed case notions come from these two logs, where object types such as a written parliamentary question or a farm are separate sub-processes; it is no surprise that a farm does not see the rest of a game. Figure 2 shows both measures for every log.

Narrowing does not disappear when we restrict attention to plausible case notions (section 3.4). Fifteen case notions cover at least half of their log's events, and 2 of them are narrowed. The Villager case notion of Age of Empires II covers 52.8% of the events but shows 17% of the activities. The Assessment case notion of OULAD covers 80% of the events but shows only one of three activities: every submission is visible, while every registration and withdrawal is lost. More importantly, in two logs no case notion is plausible at all. The widest case notion covers 32.8% of the Bundestag events (and shows 3% of its 148 activities) and 37.4% of the Ethereum window. In these logs every flat view is a partial view, whichever object type the analyst chooses. In the other five logs the widest case notion covers at least 95% of the events and shows at least 97% of the activities.

These counts are stable under our thresholds. With the narrowing threshold at 0.3, 0.4, 0.5, 0.6 and 0.7, the number of narrowed case notions is 17, 18, 20, 20 and 20 of 38. With the coverage threshold for plausible case notions at 30%, 40%, 50%, 60% and 70%, the plausible case notions number 21, 16, 15, 13 and 13, of which 5, 3, 2, 1 and 1 are narrowed; OULAD Assessment is narrowed at every threshold. Raising the event cut-off from 1,000 to 2,000 and 5,000 leaves 33 and 28 case notions, of which 15 and 10 are narrowed.

![Figure 2. Activity-ranking agreement per log. Blue: duplication alone (worst case notion). Orange: against the whole process (median case notion).](fig_rank_activity.png)

**Careless counting can mislead.** Suppose an analyst ranks entities (people, for example) by the number of rows they appear in in a denormalised flat export, and compares this with the true number of events per entity. Over the entities that appear in the export (Figure 3), the worst-case ρ is 0.16 in Enron, -0.01 in Ethereum and -0.41 in Age of Empires II. An analyst who de-duplicates on the event identifier avoids this, so the finding is a warning about counting rows rather than a loss that cannot be avoided.

![Figure 3. Entity-ranking agreement from a denormalised flat export, per log: median over entity types and worst entity type.](fig_rank_entity.png)

**Edges show a smaller effect.** Angular has the largest duplication of directly-follows pairs (74 copies for the branch case notion). Where nested children exist, some flat edges join events that are adjacent in the flat log but unrelated in the data. These spurious edges make up at most 27.7% of adjacent pairs in Age of Empires II and 16.6% in OULAD.

## 5. Discussion

We began by expecting that flattening mainly duplicates events. The data did not support this. Duplication is large in only two of the seven logs. What appears far more often is that a case notion sees only part of the process, and the flat log gives no indication of what is missing.

Much of this narrowing is structural and, to an informed analyst, expected: a case notion for one kind of procedure will not show other kinds. We think it is still worth measuring, for two reasons. First, an analyst does not always know the structure of a log before flattening it, and in two of our seven logs no single object type covers even half of the events. Second, narrowing also occurs in case notions that look like reasonable choices. The OULAD Assessment view covers 80% of the events and would appear complete, yet it cannot show a single withdrawal. If the reader takes one habit from this paper, we hope it is this: before trusting a flat result, ask which events and activities the case notion never saw.

Three practical rules follow.

1. Report the share of events and activities a case notion covers next to any flat result. These are two numbers, and they are the cheapest warning we found.
2. De-duplicate on the event identifier before counting anything, and count entities from the object-centric tables.
3. If objects of one type are shared across the cases of another (the coupling numbers), do not treat the cases as independent.

**What this might mean for capstone review.** We can offer only a hypothesis. A capstone portal's documented audit log relates each action to one project and to the person who acted. If real data has that shape, flattening on the project would copy few events, but it would hide how one guide's reviews spread across many projects, and it would hide the people. That is the narrowing pattern, not the duplication pattern. We tested nothing on portal data, so we make no claim about it, and a de-identified portal log is the obvious next test.

## 6. Threats to validity

*Seven logs.* They come from several domains, but they are a purposive sample chosen for variety and availability, not a random one. The three regimes are descriptive, and we do not claim they are exhaustive.
*Our choices.* Case notions are object types (and roles, for Enron). The nested-child thresholds and the 1,000-event cut-off are ours. The plausible-case-notion criterion was added after the first results; we report it across a range of thresholds to show that the conclusion does not depend on one value.
*A window.* The Ethereum results come from 300,000 of 3.2 million events.
*A data-quality flag.* About 0.1% of the Enron events (72) have timestamps before 1990, which is odd for a 1998 to 2002 corpus. We left them in.
*Checking.* The independent implementations are independent of the code under test, not of the team. The second implementation of the distortion metrics covers slices, not full logs. The activity-ranking numbers have no second implementation. No second person labelled the findings, and a hand review of classified CROP comments was done by one of us.
*Licence.* The reference flattening uses pm4py, which is licensed under AGPL-3.0. Releasing our code means choosing a compatible licence or replacing that dependency.

## 7. Conclusion

Flattening does not mainly duplicate events. In seven real logs, duplication is large only in the fan-out logs. Narrowing, where a case notion sees under half of the process's activities, is more common: it occurs in 20 of 38 case notions. Most of these are structural, but narrowing remains in 2 of the 15 case notions that cover at least half of their log, and in two logs no case notion covers half of the events. Counting rows in a denormalised flat export can also reverse an entity ranking. The pipeline that produced these numbers re-runs with one command and was checked in parts by independent code, though not yet everywhere. The next steps are to run the second implementation on the full logs, obtain independent labelling of the findings, compare process discovery and prediction between views, add further real logs, and, if it is ever permitted, analyse a de-identified capstone-portal log.

## Declarations

**Data and code.** All seven logs are public (CC BY 4.0; OULAD licence as stated by its authors [8]). Records: Zenodo 3599150 (CROP), 8430332 (Angular), 16811928 (Bundestag), 21989732 (Enron), 21989580 (Ethereum), 13365584 (Age of Empires II); UCI doi:10.24432/C5KK69 (OULAD). Code and result files are in the project repository under `realdata/`; run `make study` to regenerate every number.
**Personal data.** Enron e-mail addresses and CROP names are hashed on load and never printed. No VIT student, guide or portal data was used.
**Synthetic data.** None.
**Author contributions (CRediT).** {{[Authors to complete: conceptualisation, methodology, software, validation, writing, supervision for each author.]}}
**Use of generative AI.** {{[Authors to complete before submission. Most publishers require this statement. Say truthfully which AI tools were used, for what (drafting text, editing, writing code), and that the authors reviewed the output and take responsibility for the content.]}}
**Competing interests and funding.** None declared; to be confirmed by the authors.

## References

[1] W. M. P. van der Aalst, "Object-centric process mining: Dealing with divergence and convergence in event data," in *Software Engineering and Formal Methods (SEFM 2019)*, Lecture Notes in Computer Science, vol. 11724. Springer, 2019, doi:10.1007/978-3-030-30446-1_1.
[2] A. Berti *et al.*, "OCEL (Object-Centric Event Log) 2.0 specification," arXiv:2403.01975, 2024.
[3] J. N. Adams, G. Park, and W. M. P. van der Aalst, "Preserving complex object-centric graph structures to improve machine learning tasks in process mining," *Engineering Applications of Artificial Intelligence*, vol. 125, art. 106764, 2023, doi:10.1016/j.engappai.2023.106764.
[4] J. N. Adams and W. M. P. van der Aalst, "Addressing convergence, divergence, and deficiency issues," in *Business Process Management Workshops (BPM 2023)*, Lecture Notes in Business Information Processing. Springer, 2024, pp. 496-507, doi:10.1007/978-3-031-50974-2_37.
[5] P. Waibel, L. Pfahlsberger, K. Revoredo, and J. Mendling, "Causal process mining from relational databases with domain knowledge," arXiv:2202.08314, 2022 (v2, 2023).
[6] M. Kabierski, M. Basmer, A. Patecka, K. Sahling, and S. Bala, "Data quality in object-centric event data: Issues classification and evaluation," *Process Science*, vol. 3, no. 1, art. 15, 2026, doi:10.1007/s44311-026-00043-x.
[7] N. Miri, S. Khayatbashi, J. Zdravkovic, and A. Jalali, "An object-centric approach to multi-entity educational process mining," *Decision Analytics Journal*, vol. 19, art. 100724, 2026, doi:10.1016/j.dajour.2026.100724.
[8] J. Kuzilek, M. Hlosta, and Z. Zdrahal, "Open University Learning Analytics dataset," *Scientific Data*, vol. 4, art. 170171, 2017, doi:10.1038/sdata.2017.171.
[9] M. Paixao, J. Krinke, D. Han, and M. Harman, "CROP: Linking code reviews to source code changes," in *Proc. 15th Int. Conf. Mining Software Repositories (MSR)*, 2018, pp. 46-49, doi:10.1145/3196398.3196466.
[10] H. Hassani *et al.*, "Supervision of undergraduate final year projects in computing: A case study," *Education Sciences*, vol. 8, no. 4, art. 210, 2018, doi:10.3390/educsci8040210.
[11] W. Premchaiswadi and P. Porouhan, "Process modeling and bottleneck mining in online peer-review systems," *SpringerPlus*, vol. 4, art. 441, 2015, doi:10.1186/s40064-015-1183-4.

*Reference check, 2026-10-27: details confirmed against publisher, arXiv, DBLP or index records for [2]-[11]. Still to confirm on the publisher page before submission: the page range of [1] (sources disagree: 1-23 and 3-25, so it is left out), the publication year printed for [4] (conference 2023, volume 2024), and whether [5] has appeared as a journal article. Page numbers of the 2026 papers [6] and [7] come from search listings.*
