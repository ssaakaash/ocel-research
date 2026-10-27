"""Chapters 5-9 and Appendix A of the Review 3 report. Result tables are generated from realdata/results at build time."""

from __future__ import annotations

import ast
import csv
import statistics
import textwrap
from pathlib import Path

from report_engine import esc, inline, para, run

LABEL = {"angular_commits": "Angular commits", "aoe2": "Age of Empires II", "bundestag": "German Bundestag", "crop": "CROP (Gerrit)", "enron": "Enron e-mail", "ethereum": "Ethereum (window)", "oulad": "OULAD"}
DOMAIN = {"angular_commits": "Software commits", "aoe2": "Game play", "bundestag": "Legislation", "crop": "Code review", "enron": "E-mail", "ethereum": "Blockchain", "oulad": "Education"}
REGIME = {"crop": "Star", "oulad": "Star", "bundestag": "Partitioned", "aoe2": "Partitioned", "ethereum": "Partitioned", "angular_commits": "Fan-out", "enron": "Fan-out"}
ORDER = ["crop", "oulad", "bundestag", "aoe2", "ethereum", "angular_commits", "enron"]


def read_rows(path: Path, key: str = "log") -> dict:
    with path.open(encoding="utf-8") as h:
        return {r[key]: r for r in csv.DictReader(h)}


def read_all(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as h:
        return list(csv.DictReader(h))


# ------------------------------------------------------------------------------------------------ chapter 5
def ch5(D):
    D.chapter_start("Methodology and Testing")
    D.h2("Module Description")
    D.p("There are seven modules, M1 to M7. Each one is a small Python script in the `realdata/src` directory, and each reads what the one before it wrote. "
        "Figure 4.1 shows how they connect.")

    D.h3("M1: Acquire and Verify")
    D.p("`fetch_sources.py` reads a manifest (`sources.json`) that lists each source with its record number, licence and expected files. "
        "For a Zenodo record it asks Zenodo for the file list, downloads each file, and compares the size and MD5 checksum with the record. A mismatch deletes the file and stops the run. "
        "OULAD comes from the UCI mirror and has no published checksum, so there we cap the download size and record the SHA-256. Every file gets a SHA-256 in a `SOURCE.md` next to it. "
        "If a download stalls, the script resumes from the partial file with an HTTP Range request; this was needed once during the study.")
    D.p("`extract_archives.py` unpacks each archive into a new, empty directory next to it, and it refuses any archive with an absolute path or a parent-relative (`..`) member path.")
    D.p("Table 5.1 lists the sources, and Table 7.1 has the sizes of the logs.")
    D.table("Sources of the seven logs",
            ["Log", "Publisher and record", "Authors of the dataset"],
            [["CROP (Gerrit)", "Zenodo 3599150", "Paixao, Krinke, Han, Harman"],
             ["OULAD", "UCI repository, DOI 10.24432/C5KK69", "Kuzilek, Hlosta, Zdrahal"],
             ["Angular commits", "Zenodo 8430332", "Pegoraro"],
             ["German Bundestag (20th period, filtered)", "Zenodo 16811928", "Diers, Peeva, Rennert, van der Aalst"],
             ["Enron e-mail (top 100,000 mails)", "Zenodo 21989732", "Berti"],
             ["Ethereum DApps (300,000-event window)", "Zenodo 21989580", "Berti"],
             ["Age of Empires II (10-match filter)", "Zenodo 13365584", "Liss, Elbert, Flath"]],
            [2.4, 2.4, 2.2])

    D.h3("M2: Convert and Load")
    D.p("Five logs already come in an OCEL format: Angular and Bundestag as JSON, Age of Empires as SQLite, Enron and Ethereum as parquet bundles. "
        "For the other two, `convert_crop.py` and `convert_oulad.py` build OCEL 2.0 SQLite files. "
        "CROP becomes three object types (change, person, project) with events like upload, comment, approve, merge and abandon. "
        "OULAD becomes four (student, enrollment, presentation, assessment) with events like register, submit and unregister.")
    D.p("`ocel_io.py` loads every format into the same four pandas tables. It hashes personal identifiers with a salted hash (the Enron e-mail addresses and the CROP names), "
        "splits the Enron e-mail address type by role (sender, recipient, copied) so each role can be a case notion, and for Ethereum cuts a contiguous window of 300,000 events. "
        "The flattening function used throughout the study is also defined there.")

    D.h3("M3: Distortion Metrics")
    D.p("A //case notion// is an object type we choose as the case. Flattening on type //T// gives one row for every distinct pair of an event and a T-object, the same as the flattening function in `pm4py`. "
        "Events with several T-objects are repeated, events with none are dropped, and only event-level attributes survive. "
        "A case notion counts as //analysed// when it covers at least 1,000 events, which leaves 38 case notions over the seven logs. Table 5.2 defines the metrics.")
    D.table("Distortion metrics for a case notion T",
            ["Metric", "Definition", "How to read it"],
            [["Deficiency", "Share of events with no T-object", "Events a flat view drops"],
             ["Convergence share", "Share of covered events related to two or more T-objects", "Events copied into several cases"],
             ["Copies per event", "Flat rows divided by covered events", "Inflation of event counts (1.0 means none)"],
             ["Divergence share", "Share of (case, activity) pairs with two or more events whose other-object sets differ", "Repeated events that belong to different objects"],
             ["Nested child", "Another type U whose objects are almost exclusive to one case (95% or more), have their own lifecycle (two or more events) and a fan-out of at least 1.5 per case", "Items of an order, for example"],
             ["Cross-instance adjacency", "Among directly-follows pairs in cases with two or more nested children, the share whose two events concern disjoint children", "Events adjacent in the flat log but unrelated in the data"],
             ["Coupling", "For an ordered pair of types (T, U), the share of U-objects that touch two or more T-objects", "How much the cases share objects"],
             ["Variants per case", "Distinct activity sequences divided by cases", "How scattered the flat behaviour looks"]],
            [1.5, 3.4, 2.2], sz=18)
    D.p("The thresholds (95% exclusivity, fan-out of 1.5, 1,000 events) are our own choices. They sit at the top of `distortion.py` and `consequence.py`, and none of them was tuned to improve a result.")

    D.h3("M4: Consequence Analysis")
    D.p("Distortion metrics tell us how much a flat view differs. The consequence analysis asks what an analyst would read differently. "
        "The reference is the object-centric view: every event counted once, plus the object-centric directly-follows relation, which is the union of consecutive-event pairs over the lifecycle of every object of every type. "
        "For each case notion we compare four outputs against that reference, and then we look at the process model an analyst would discover from the flat log.")
    D.bullets([
        "C1, activity ranking: Spearman rank correlation of the flat activity counts with (a) the counts of the whole process, each event once, and (b) the counts of the same covered events each counted once, which isolates the effect of duplication. We also report the share of activities visible at all.",
        "C2, directly-follows edges: duplication of event pairs (flat pairs divided by distinct pairs), rank agreement of edge frequencies with and without duplicates, the largest inflation among the ten most frequent reference edges, and, when nested children exist, the share of flat edge instances whose edge type never occurs inside any child (the spurious edge mass).",
        "C3, variants: distinct activity sequences, variants per case, and the share of cases covered by the ten most frequent variants.",
        "C4, entity ranking: for every other object type with at least 30 objects, the rank correlation between the true number of events per object and the row count that a denormalised flat export of T would give, over the objects that appear in the export at all.",
        "C5, discovered model: the Inductive Miner with infrequent-behaviour filtering [12] (noise threshold 0.2, as implemented in `pm4py` [15]) runs on each flat log. We score the model on the same flat log with token-based replay fitness [13] and token-based precision [14], "
        "and we record the size of the process tree, its //loop share// (the share of its visible activities that sit under a loop operator) and the share of the process's activities that the model contains at all.",
    ])
    D.p("Precision replays every prefix of every case, so its cost grows with the square of case length. We compute it only when the squared case lengths add up to at most 20 million, "
        "and each case notion gets an hour in total. The Inductive Miner copies its process tree with Python's `deepcopy` while simplifying it, and on cases of several thousand events that nests deeper than Python's default limit of 1,000 calls. "
        "Two Age of Empires II case notions failed for this reason in our first runs, so `discovery.py` raises the limit inside the mining process.")
    D.p("Two details matter for fairness. Events are coded by sorted event identifier, so ties in time always break the same way. "
        "And the analysis keeps //duplication// (the same event counted several times) apart from //narrowing// (events or activities a case notion never sees). "
        "An analyst can undo the first by de-duplicating on the event identifier, but the second cannot be recovered from a flat log.")
    D.p("Some object types would never be chosen as a case notion. A farm in Age of Empires II, for example, takes part in only a handful of activities. To separate this structural narrowing from narrowing that an analyst could plausibly encounter, "
        "we also look at the //widest// case notion of each log (the one covering the most events) and at //plausible// case notions, meaning those that cover at least half of the log's events. "
        "Both views were introduced after the first results were seen, so we report them over a range of thresholds rather than at 50% only.")
    D.p("Every number is computed on the full data, so the remaining uncertainty is about which events and which items happen to be in a log. `bootstrap.py` estimates it with 200 bootstrap replicates and a fixed seed. "
        "For counts of case notions it gives every event a Poisson(1) weight and recomputes coverage and visibility. For rank correlations it resamples the ranked items themselves (activities, or visible entities). "
        "An earlier version also used event weights for the correlations and produced intervals that did not contain their own estimates: an entity with a single event receives the same weight in its true count and in its row count, which creates artificial agreement. "
        "The unweighted replicate reproduces every published value, and the script checks that before it starts.")

    D.h3("M5: Predicate Engine (Appendix-Level)")
    D.p("We keep a rule-based engine from earlier work, `cooc.py` with `registry.py`. It evaluates eleven natural rules (for example, a change is merged only after an approval vote, or no submission after the assessment deadline) "
        "on native, flat and denormalised-flat views of CROP and OULAD. Two logs and eleven rules are too few to support a conclusion, so the engine is excluded from the main results.")

    D.h3("M6: Validation")
    D.p("`sql_crosscheck.py` re-implements four CROP rules in plain SQL on the OCEL SQLite file, opened read-only. `check_consequence.py` compares the fast consequence code with a slow plain-Python version on a real slice of the Enron log. "
        "`check_distortion.py` does the same for the distortion metrics, using only dictionaries and sets. By default it runs on 6,000-event slices of Enron, Bundestag and Age of Empires II, and with `--full` (part of `make study`) it recomputes every metric on all seven full logs and compares the result with the published files. "
        "Finally, the OULAD counts are recomputed independently from the raw CSV files. Section 5.2 reports the results.")
    D.h3("M7: Summaries")
    D.p("`summarize_distortion.py`, `summarize_log_level.py`, `summarize_consequence.py` and `summarize_discovery.py` combine the per-log JSON files into the CSV and Markdown tables used in Chapter 7. "
        "`make study` runs the main sequence and the full-log check, and `make extended` runs the bootstrap and the process-discovery comparison, which take much longer.", jc="left")

    D.h2("Testing")
    D.p("We tested the project as we would test an external piece of work. Table 5.3 lists each check, what it establishes and its outcome.")
    D.table("Verification checks",
            ["Check", "What it proves", "Result"],
            [["Download integrity", "Zenodo files match the published size and MD5", "Verified for the Zenodo sources; SHA-256 recorded for every file, including OULAD"],
             ["Reproducibility", "Re-running gives the same outputs", "Tracked result files were byte-identical after a re-run (checked with Git)"],
             ["SQL cross-check", "The predicate code matches independent SQL", "4 of 4 CROP rules match exactly: 522, 19,109, 164 and 423 flagged changes"],
             ["Brute-force self-check", "The fast consequence code equals plain Python", "Directly-follows pairs identical on 4 case notions; entity ranking identical"],
             ["Distortion self-check", "The pandas distortion metrics equal a plain-Python version", "Identical on all seven full logs: 87 case notions (every object type) and 294 type pairs"],
             ["Bootstrap reproduction", "The resampling code computes the same statistics as the analysis", "The unweighted replicate matches all 38 case notions exactly"],
             ["Independent recomputation", "OULAD counts match the raw CSV files", "15,348 enrolments with a late submission, 415 submissions after unregistration, 29 flagged by the stage-order rule: all exact"],
             ["Bugs found by our own checks", "The checks detect real errors", "Three bugs found and fixed (see below)"]],
            [1.7, 2.3, 3.0], sz=18)
    D.p("The checks caught three bugs of our own, and we fixed all three before producing the results in this report.")
    D.bullets([
        "Duplicate events: the CROP converter wrote duplicate event rows, about 17% of them. They are removed.",
        "A missed abandon form: the converter did not recognise one phrasing of the Gerrit abandon message (\"Patch Set N: Abandoned\"). It does now.",
        "Tie-breaking: events with the same timestamp could be ordered differently in two code paths. Events are now ordered by timestamp and then by event identifier.",
    ])
    D.p("Some checks were not carried out. No one outside the team labelled the findings. We reviewed a stratified sample of classified CROP comments by hand and found no further misclassification, "
        "but the reviewer was one of us, so it is not an independent label set. The converters are checked by us, not by a second team, and the SQL cross-check tests the predicate code, not the CROP converter. "
        "The activity-ranking numbers are recomputed only by the bootstrap code, which loads the data the same way as the analysis it checks.")


# ------------------------------------------------------------------------------------------------ chapter 6
def ch6(D, demo_dir: Path):
    D.chapter_start("Project Demonstration")
    D.p("The live demonstration runs five commands from the `realdata` directory. We ran them for this report and saved the output under `docs/review-3/demo/`, "
        "so that the same output can be shown if network or hardware problems occur during the review. Table 6.1 lists the steps and the measured times.")
    D.table("Demonstration steps",
            ["Step", "Command", "What the panel sees", "Time"],
            [["1", "`python3 -I src/fetch_sources.py`", "All eight sources already present; nothing is downloaded again", "0.1 s"],
             ["2", "`.venv/bin/python -I src/check_consequence.py`", "Self-check against the plain-Python version", "3.7 s"],
             ["3", "`.venv/bin/python -I src/distortion.py enron`", "Distortion table for the Enron log", "9.5 s"],
             ["4", "`.venv/bin/python -I src/consequence.py enron`", "Rankings, edges, variants and entities for Enron", "4.1 s"],
             ["5", "`head -4 results/consequence_by_log.md`", "The cross-log summary table", "instant"]],
            [0.5, 3.0, 2.8, 0.8], sz=18, align=["center", "left", "left", "center"])

    def show(title: str, fname: str, keep: int | None = None, width: int = 92):
        D.h4(title)
        text = (demo_dir / fname).read_text(encoding="utf-8").rstrip("\n").split("\n")
        lines = []
        for ln in text:
            if ln.startswith("=== ") or ln.strip() == "":
                pass
            for part in (textwrap.wrap(ln, width=width, subsequent_indent="      ", break_long_words=True) or [""]):
                lines.append(part)
        if keep:
            lines = lines[:keep]
        D.code(lines, sz=16)

    D.h2("Step 1: Check that the data is present")
    show("Command: python3 -I src/fetch_sources.py", "1_fetch.txt")
    D.p("The manifest lists eight sources, and all of them are already on disk with a `SOURCE.md`, so the script skips them. On a clean machine the same command downloads about 350 MB.")
    D.h2("Step 2: Run the self-check")
    show("Command: .venv/bin/python -I src/check_consequence.py", "2_check.txt")
    D.p("The fast consequence code and a plain-Python version agree on a real Enron slice. The directly-follows pairs are identical for four case notions, and so is the entity ranking.")
    D.h2("Step 3: Distortion of the Enron log")
    show("Command: .venv/bin/python -I src/distortion.py enron", "3_distortion.txt")
    D.p("Four case notions get flattened: the three e-mail roles and the message identifier. Take the copied-in recipients as the case (EMAILADDRESS:CC) and 77.8% of the events drop out, "
        "while the remaining events are copied 2.11 times on average. The message identifier drops 40.1% and copies nothing. "
        "The coupling lines show how strongly the cases are interlinked: 81% of the \"to\" addresses take part in events that belong to two or more different \"cc\" cases (6.4 on average).")
    D.h2("Step 4: Consequences for the Enron log")
    show("Command: .venv/bin/python -I src/consequence.py enron", "4_consequence.txt")
    D.p("Each line is one case notion. For the copied-recipient notion only 77.8% of the activities are visible, and the activity ranking agrees with the whole process at a rank correlation of 0.87. "
        "Measured for duplication alone, the correlation is exactly 1.0, so nearly all of that gap is due to narrowing.")
    D.h2("Step 5: The cross-log summary")
    D.h4("Command: head -4 results/consequence_by_log.md")
    D.p("The command prints a Markdown table with one row per log. The lines are too wide for a printed page, so we do not copy them here. "
        "The saved output is in `docs/review-3/demo/5_table.txt`, and Table 7.3 in Chapter 7 shows the same numbers.")
    D.p("`make study` re-runs everything. When we ran it for this report it finished without error in 5 minutes 21 seconds and left every tracked result file unchanged (checked with Git).")

# ------------------------------------------------------------------------------------------------ chapter 7
def f(x, nd=2):
    if x in (None, ""):
        return "-"
    v = round(float(x), nd)
    return f"{(v if v else 0.0):.{nd}f}"


def ci(Q, key, nd=2):
    q = Q[key]
    return f"{q['ci_low']:.{nd}f} to {q['ci_high']:.{nd}f}"


def ch7(D, res: Path):
    import json
    Q = json.loads((res / "bootstrap.json").read_text(encoding="utf-8"))["quantities"]
    L = read_rows(res / "log_level_summary.csv")
    C = read_rows(res / "consequence_by_log.csv")
    N = read_all(res / "consequence_by_notion.csv")
    D.chapter_start("Result and Discussion")
    D.p("Every number in this chapter comes from the files in `realdata/results` and regenerates with `make study`. "
        "These are measurements on seven real public logs. They say nothing about the capstone portal.")

    D.h2("The Seven Logs")
    D.table("Profile of the seven logs",
            ["Log", "Domain", "Events", "Objects", "Object types", "Objects per event", "Analysed case notions"],
            [[LABEL[k], DOMAIN[k], f"{int(L[k]['events']):,}", f"{int(L[k]['objects']):,}", L[k]["types"], f(L[k]["objects_per_event"], 1), L[k]["case_notions_covering_ge1000_events"]] for k in ORDER],
            [1.7, 1.3, 0.9, 0.9, 0.8, 0.9, 0.9], sz=18, align=["left", "left", "right", "right", "center", "right", "center"])
    D.p("The logs cover code review, education, legislation, e-mail, blockchain and game play, which gives 38 analysed case notions. "
        "The Ethereum figures are for a contiguous window of 300,000 events from a log with 3.2 million.")

    D.h2("Distortion by Flattening")
    D.table("Flattening distortion per log (analysed case notions)",
            ["Log", "Regime", "Median share of events dropped", "Median copies per event", "Largest copies per event", "Notions with over 5% duplication", "Type pairs sharing 50% or more"],
            [[LABEL[k], REGIME[k], f"{100 * float(L[k]['median_deficiency']):.1f}%", f(L[k]["median_copies_per_event"]), f(L[k]["max_copies_per_event"]), f"{L[k]['notions_with_event_duplication_gt5pct']} of {L[k]['case_notions_covering_ge1000_events']}",
              f"{L[k]['pairs_with_ge50pct_shared_objects']} of {L[k]['type_pairs']}"] for k in ORDER],
            [1.5, 1.0, 1.0, 0.9, 0.9, 1.0, 1.0], sz=17, align=["left", "left", "right", "right", "right", "center", "center"])
    D.p("The logs fall into three groups, shown in Figure 7.1.")
    D.p("In the star logs (CROP and OULAD) every event touches exactly one object of each type. Flattening copies nothing (1.00 copies per event) and, in the median, drops nothing. On these two measures the distortion is zero.")
    D.p("The partitioned logs (Bundestag, Age of Empires II, Ethereum) copy little, at most 1.27, 1.76 and 1.09 copies per event. However, different object types cover different parts of the log, "
        "so the median case notion drops between 69% and 91% of the events.")
    D.p("In the fan-out logs (Angular commits and Enron) one event relates to many objects of the same type. The largest duplication is 81.65 copies per event in Angular (the branch case notion) and 2.11 in Enron.")
    D.figure("fig_regimes.png", "Duplication and dropped events for the seven logs, by regime", 5.6)
    D.p("Coupling adds a second perspective. Figure 7.2 shows the share of object-type pairs where the objects of one type are shared across the cases of the other. "
        "In every log except the Bundestag and Age of Empires, at least half the type pairs share more than half of their objects, and in Angular both of the two pairs do.")
    D.figure("fig_coupling.png", "Object-type pairs that share more than half of their objects across cases", 5.4)

    D.h2("Consequences for Standard Outputs")
    D.table("Consequences of flattening per log",
            ["Log", "Notions", "Activities visible (median)", "Activity rank correlation, whole process (median / lowest)", "Lowest, duplication only", "Largest edge duplication", "Lowest entity-rank correlation"],
            [[LABEL[k], C[k]["notions"], f(C[k]["activity_visible_share_median"]), f"{f(C[k]['activity_rank_rho_all_median'])} / {f(C[k]['activity_rank_rho_all_min'])}", f(C[k]["activity_rank_rho_dup_only_min"]),
              f(C[k]["df_pair_duplication_max"]), f(C[k]["entity_rho_visible_min"])] for k in ORDER],
            [1.4, 0.7, 0.9, 1.5, 0.9, 0.9, 0.9], sz=16, align=["left", "center", "right", "center", "right", "right", "right"])
    dup_low = [(r["log"], r["case_type"], float(r["act_rank_rho_dup_only"])) for r in N if float(r["act_rank_rho_dup_only"]) < 0.95]
    narrow = sum(1 for r in N if float(r["act_visible_share"]) < 0.5)
    D.p("Three findings follow from this table.")
    D.p(f"First, duplication alone rarely changes a ranking. When the activity ranking from flat rows is compared with the ranking of the same events counted once, "
        f"and only {len(dup_low)} of the {len(N)} case notions fall below a rank correlation of 0.95 (bootstrap interval {Q['dup_below_095']['ci_low']:.0f} to {Q['dup_below_095']['ci_high']:.0f}): "
        f"Angular files ({dup_low[0][2]:.2f}, interval {ci(Q, 'angular_commits:rho_dup_min')}) and the Enron \"to\" role ({dup_low[1][2]:.2f}). The Enron value is less certain: with only nine activities, its interval runs from {ci(Q, 'enron:rho_dup_min')}. "
        "Where a log has no duplication, as in the star logs, the correlation is exactly 1.0.")
    D.p(f"Second, narrowing is the bigger effect. In {narrow} of the {len(N)} case notions the flat log shows fewer than half of the activities of the whole process. "
        f"The activity rank correlation with the whole process has a median of only 0.17 in the Bundestag (interval {ci(Q, 'bundestag:rho_all_median')}) and 0.21 in Age of Empires II ({ci(Q, 'aoe2:rho_all_median')}). "
        "A flat view of those logs is therefore not a distorted picture of the whole process but a small part of it.")
    D.p("Much of this narrowing is structural. Eighteen of the 20 narrowed case notions come from the Bundestag and Age of Empires II, where an object type such as a written parliamentary question or a farm is in effect a sub-process of its own, and a farm cannot be expected to see the rest of the game. "
        "We therefore also examined the case notions an analyst would plausibly choose. Fifteen of them cover at least half of their log, and 2 of those are still narrowed. "
        "Villager, in Age of Empires II, covers 52.8% of the events but shows 17% of the activities. OULAD's Assessment case notion covers 80% of the events and shows one activity in three: every submission is present, while every registration and withdrawal is lost. "
        "More importantly, two logs have no plausible case notion at all. The widest case notion covers 32.8% of the Bundestag events (and 3% of its 148 activities) and 37.4% of the Ethereum window. In the other five logs the widest case notion covers at least 95% of the events.")
    D.p("These counts do not depend on a single threshold. With the narrowing threshold at 0.3, 0.4, 0.5, 0.6 and 0.7, the number of narrowed case notions is 17, 18, 20, 20 and 20. "
        "With the coverage threshold at 30% to 70%, there are 21, 16, 15, 13 and 13 plausible case notions, of which 5, 3, 2, 1 and 1 are narrowed, and OULAD Assessment is narrowed every time. "
        f"Raising the 1,000-event cut-off to 2,000 or 5,000 leaves 15 of 33 and 10 of 28 narrowed. In all 200 bootstrap replicates the counts remain at {Q['narrowed']['estimate']:.0f} narrowed, {Q['plausible']['estimate']:.0f} plausible and {Q['plausible_narrowed']['estimate']:.0f} both.")
    D.figure("fig_rank_activity.png", "Activity ranking agreement: duplication alone versus the whole process", 5.6)
    D.p("Third, careless counting can mislead. Suppose an analyst ranks entities (people, for example) by counting rows in a denormalised flat export. "
        f"Among the entities that appear in the export, the worst-case rank correlations with the true number of events per entity are 0.16 in Enron (interval {ci(Q, 'enron:entity_min')}), -0.01 in Ethereum ({ci(Q, 'ethereum:entity_min')}) and -0.41 in Age of Empires II ({ci(Q, 'aoe2:entity_min')}). "
        "An analyst who de-duplicates on the event identifier would avoid this, so this result is a warning about careless counting rather than an unavoidable loss.")
    D.figure("fig_rank_entity.png", "Entity ranking agreement from a denormalised flat export", 5.6)
    D.p("Directly-follows edges show a smaller but measurable effect. Angular has the largest duplication of event pairs (74 copies for the branch case notion). "
        "Where nested children exist, some flat edges join events that are adjacent in the flat log but unrelated in the data. "
        "These spurious edges account for at most 27.7% in Age of Empires II and 16.6% in OULAD.")
    D.figure("fig_spurious.png", "Spurious directly-follows edges, worst case notion per log", 5.4)
    discovery_section(D, res)

    D.h2("Discussion")
    D.p("Our initial expectation was that flattening mainly duplicates events. The data did not support this. Duplication is large in only two of the seven logs. "
        "The common pattern is that a case notion sees only part of the process, and the flat log gives no indication of what is missing. "
        "The usual quality check does not reveal this: a model discovered from a narrowed flat log still replays that log almost perfectly, so fitness remains high precisely when the view is most partial.")
    D.p("For the capstone, only a hypothesis can be stated, since no portal data is available. The portal's documented audit log relates each action to one project and to the person who acted. "
        "If real data has that shape, flattening on the project would copy few events, but it would hide how one guide's reviews spread across many projects, and it would hide the people. "
        "That is the narrowing pattern, not the duplication pattern. The next step is to test this on a de-identified portal log. Until then we make no claim about the portal.")
    D.h3("Threats to Validity")
    D.bullets([
        "Seven logs from several domains: the three regimes are descriptive, and we do not claim that they are exhaustive.",
        "Our choices: case notions are object types (and roles for Enron), and the thresholds for nested children and for the minimum case-notion size are ours, written in the code.",
        "A window of Ethereum: those results come from a contiguous window of 300,000 events.",
        "A data-quality flag in Enron: about 0.1% of the events (72) have timestamps before 1990, which is unusual for a corpus from 1998 to 2002. They were retained.",
        "Checks by us: the independent implementations are independent of the code under test, not of the team, and no one outside the team labelled the findings.",
        "One miner: the discovery comparison uses one algorithm with one noise threshold, and other miners may well give different models.",
    ])

    D.h2("Cost Analysis")
    D.p("By cost we mean the money and effort to produce or reproduce the study. Table 7.5 summarises it.")
    D.table("Cost of producing and reproducing the study",
            ["Item", "Producing the study", "Reproducing it"],
            [["Data", "Nil (open data, CC BY 4.0)", "About 350 MB download for the core set"],
             ["Software", "Nil (open-source libraries; `pm4py` is AGPL-3.0)", "Python 3.14 and the pinned packages in `requirements.txt`"],
             ["Hardware", "A laptop the team already owned (8 GiB memory)", "Any laptop with 8 GiB of memory or more"],
             ["Cloud or paid services", "None", "None"],
             ["Run time", "Seconds to minutes per log", "About 4 to 10 seconds for the Enron log; `make study` for all seven logs took 5 minutes 21 seconds"]],
            [1.4, 3.0, 2.6], sz=18)
    D.p("The main cost is the team's time, much of it spent on verification. The monetary cost is nil.")


NOTION_EN = {"Gesetzgebung": "legislation", "ORDER": "orders", "Player": "player", "Antrag": "motions", "Rechtsverordnung": "statutory orders"}


def notion_name(r: dict) -> str:
    t = r["case_type"]
    return f"{LABEL[r['log']].replace(' (window)', '')} {NOTION_EN.get(t, t)}" + (f" ({t})" if t in NOTION_EN and NOTION_EN[t].lower() != t.lower() else "")


def pretty_unfinished(items: list[str]) -> str:
    out = []
    for it in items:
        key, rest = it.split("/", 1)
        name, _, why = rest.partition(" (")
        why = why.rstrip(")")
        reason = {"time budget": "it exceeded the time budget"}.get(why, "the mining process failed" if why.startswith("child exit") else why)
        out.append(f"{LABEL[key]} {name} ({reason})")
    return "; ".join(out)


def discovery_section(D, res: Path):
    import json
    S = json.loads((res / "discovery_summary.json").read_text(encoding="utf-8"))
    rows = read_all(res / "discovery_by_notion.csv")
    per = {}
    for f in sorted((res / "discovery").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        per[d["log"]] = len(d["notions"])
    narrowed = [r for r in rows if float(r["act_visible_share"]) < 0.5]
    prec = sorted(((float(r["precision"]), r) for r in rows if r["precision"] not in ("", "None")), key=lambda t: t[0])
    D.h2("Process Discovery on Flat Logs")
    D.p(f"Process discovery is the most common use of process mining, so we discovered a model from every flat log (C5 in Section 5.1). It finished for {S['notions']} of the {sum(per.values())} case notions. "
        + (f"The remaining {len(S['not_completed'])} did not finish: {pretty_unfinished(S['not_completed'])}. " if S["not_completed"] else "")
        + "Table 7.4 summarises the results per log.")
    tab = []
    for k in ORDER:
        rs = [r for r in rows if r["log"] == k]
        if not rs:
            continue
        pr = [float(r["precision"]) for r in rs if r["precision"] not in ("", "None")]
        pm = statistics.median(pr) if pr else None
        tab.append([LABEL[k], f"{len(rs)} of {per[k]}", f"{min(float(r['fitness']) for r in rs):.3f}", f"{pm:.2f} ({len(pr)})" if pr else "-",
                    str(sum(float(r["loop_share"]) >= 0.9 for r in rs if r["loop_share"] not in ("", "None"))), str(sum(float(r["activity_coverage"]) < 0.5 for r in rs))])
    D.table("Process discovery on the flat logs (Inductive Miner, noise threshold 0.2)",
            ["Log", "Mined", "Lowest fitness", "Median precision (notions)", "Models with 90% or more of activities in loops", "Models with under half of the activities"],
            tab, [1.5, 0.8, 0.9, 1.2, 1.4, 1.3], sz=17, align=["left", "center", "right", "right", "center", "center"])
    D.p(f"First, every model appears to be of high quality. Replay fitness runs from {S['fitness_min']:.3f} to 1.000, with a median of {S['fitness_median']:.3f}. "
        f"All {len(narrowed)} narrowed case notions are in that range, yet {S['model_covers_under_half_of_activities']} of the models contain fewer than half of the process's activities. "
        "Fitness is measured against the flat log from which the model was discovered, so it cannot reflect what flattening removed. Figure 7.6 illustrates this: the points on the left represent models of a small fraction of the process, and they score as well as the complete ones.")
    D.figure("fig_discovery.png", "Replay fitness against the share of the process's activities in the discovered model, one dot per case notion", 5.6)
    lp = S["spearman"]["loop_share~divergence_share"]["rho"]
    D.p(f"Second, divergence appears as loops. When a flat case collects repeated events that belong to different objects, the miner tends to place them inside a loop. Across case notions the loop share rises with the divergence share (Spearman rank correlation {lp:.2f}). "
        f"At least 90% of the activities sit under a loop in {S['high_divergence_with_loop_share_ge_0.9']} of the {S['high_divergence_notions']} case notions with a divergence share of 0.5 or more, "
        f"and in only {S['low_divergence_with_loop_share_ge_0.9']} of the rest. Precision, which could be computed for {S['precision_computed']} case notions, shows the consequence. "
        f"Its median is {S['precision_median']:.2f}, and the lowest values ({', '.join(f'{p:.2f} for {notion_name(r)}' for p, r in prec[:3])}) all come from models in which nearly every activity is inside a loop, so the models accept almost any order of events.")
    D.p("Given the number of case notions and the seven logs, we interpret these correlations as tendencies rather than general laws.")


# ------------------------------------------------------------------------------------------------ chapter 8
def ch8(D):
    D.chapter_start("Conclusion")
    D.p("We set out to study capstone review processes with OCEL 2.0. Portal logs were not available, so the project turned into two things: a documented OCEL 2.0 design of the capstone lifecycle, "
        "and a measurement of the effects of flattening on seven real public logs. The main conclusions are as follows.")
    D.p("First, a reproducible and verified pipeline has been built. It downloads and verifies seven public logs, converts two of them to OCEL 2.0, computes distortion metrics for 38 case notions "
        "and compares standard outputs between flat and object-centric views. A second, plain-Python implementation reproduces the distortion metrics exactly on all seven full logs, other independent checks agree with the parts they cover, "
        "and the checks caught three bugs of our own, which we fixed.")
    D.p("Second, flattening does not mainly duplicate events. Duplication is large only in the fan-out logs, up to 81.65 copies of an event in Angular, "
        "and only 2 of 38 case notions fall below a rank correlation of 0.95 because of duplication alone.")
    D.p("Third, the larger effect is narrowing. In 20 of 38 case notions the flat log shows fewer than half of the process's activities. Most of that comes from the structure of the logs, "
        "but 2 of the 15 case notions that cover at least half of their log are narrowed too, and in two logs no case notion covers half of the events. The counts hold across every threshold we tried and in every bootstrap replicate.")
    D.p("Fourth, the usual quality checks do not detect narrowing. A model discovered from a narrowed flat log still replays that log with a fitness of 0.955 or more, and divergence turns into loops that accept almost any order of events.")
    D.p("Fifth, careless counting from a flat export can be seriously misleading. Worst-case entity rankings reach a rank correlation of 0.16 (Enron), -0.01 (Ethereum) and -0.41 (Age of Empires II), and none of the bootstrap intervals exceeds 0.2.")
    D.p("Sixth, the capstone model remains a design. We could not test it on portal data, and we claim nothing about how real capstone teams behave.")
    D.p("The measurement part of this work is written up as a journal paper, //What Does Flattening Hide? Measuring Case-Notion Distortion and Its Consequences on Seven Real Object-Centric Event Logs//, "
        "which we submitted to the Journal of Intelligent Information Systems (Springer) in October 2026. It is under review.")
    D.h2("Limitations")
    D.p("We have seven logs from five domains, and one of them is a window. The thresholds are ours, and the idea of a plausible case notion came after we had seen the first results. "
        "The checks are independent of the code under test but not of the team, no one outside the team has labelled the findings, and the activity-ranking numbers are re-computed only by the bootstrap code. "
        "The discovery comparison uses one miner. The rule-based engine covers eleven rules on two logs, and we use it for no conclusion.")
    D.h2("Future Work")
    D.bullets([
        "Get independent two-rater labelling of the real-data findings.",
        "Compare predictive monitoring between flat and object-centric logs, and repeat the discovery comparison with other miners.",
    ])


# ------------------------------------------------------------------------------------------------ chapter 9 + appendix
REFS = [
    ("W. M. P. van der Aalst, \"Object-centric process mining: Dealing with divergence and convergence in event data,\" in //Software Engineering and Formal Methods (SEFM)//, Lecture Notes in Computer Science. Springer, 2019, pp. 3-25."),
    ("A. Berti //et al.//, \"OCEL (Object-Centric Event Log) 2.0 specification,\" arXiv:2403.01975, 2024."),
    ("J. N. Adams, G. Park, and W. M. P. van der Aalst, \"Preserving complex object-centric graph structures to improve machine learning tasks in process mining,\" //Engineering Applications of Artificial Intelligence//, vol. 125, p. 106764, 2023."),
    ("J. N. Adams and W. M. P. van der Aalst, \"Addressing convergence, divergence, and deficiency issues,\" Lecture Notes in Business Information Processing. Springer, 2024."),
    ("P. Waibel, L. Pfahlsberger, K. Revoredo, and J. Mendling, \"Causal process mining from relational databases with domain knowledge,\" arXiv:2202.08314, 2022."),
    ("M. Kabierski //et al.//, \"Data quality in object-centric event data: Issues classification and evaluation,\" //Process Science//, vol. 3, 2026."),
    ("N. Miri, S. Khayatbashi, J. Zdravkovic, and A. Jalali, \"An object-centric approach to multi-entity educational process mining,\" //Decision Analytics Journal//, vol. 19, p. 100724, 2026."),
    ("J. Kuzilek, M. Hlosta, and Z. Zdrahal, \"Open University Learning Analytics dataset,\" //Scientific Data//, vol. 4, p. 170171, 2017."),
    ("M. Paixao, J. Krinke, D. Han, and M. Harman, \"CROP: Linking code reviews to source code changes,\" in //Proc. Mining Software Repositories (MSR)//, 2018."),
    ("H. Hassani //et al.//, \"Supervision of undergraduate final year projects in computing: A case study,\" //Education Sciences//, vol. 8, no. 4, p. 210, 2018."),
    ("W. Premchaiswadi and P. Porouhan, \"Process modeling and bottleneck mining in online peer-review systems,\" //SpringerPlus//, vol. 4, p. 441, 2015."),
    ("S. J. J. Leemans, D. Fahland, and W. M. P. van der Aalst, \"Discovering block-structured process models from event logs containing infrequent behaviour,\" in //Business Process Management Workshops (BPM 2013)//, Lecture Notes in Business Information Processing, vol. 171. Springer, 2014, pp. 66-78."),
    ("A. Berti and W. M. P. van der Aalst, \"Reviving token-based replay: Increasing speed while improving diagnostics,\" in //Proc. Algorithms and Theories for the Analysis of Event Data (ATAED 2019)//, CEUR Workshop Proceedings, vol. 2371, 2019, pp. 87-103."),
    ("J. Munoz-Gama and J. Carmona, \"A fresh look at precision in process conformance,\" in //Business Process Management (BPM 2010)//, Lecture Notes in Computer Science, vol. 6336. Springer, 2010, pp. 211-226."),
    ("A. Berti, S. van Zelst, and D. Schuster, \"PM4Py: A process mining library for Python,\" //Software Impacts//, vol. 17, p. 100556, 2023."),
    ("Datasets used (all CC BY 4.0): German Bundestag, Zenodo record 16811928 (H. Diers, V. Peeva, C. Rennert, W. M. P. van der Aalst); Enron e-mail OCEL, Zenodo 21989732 (A. Berti); "
     "Ethereum execution data, Zenodo 21989580 (A. Berti); Age of Empires II, Zenodo 13365584 (L. Liss, N. Elbert, C. M. Flath); Angular commits, Zenodo 8430332 (M. Pegoraro); "
     "CROP, Zenodo 3599150 (M. Paixao, J. Krinke, D. Han, M. Harman); OULAD, UCI Machine Learning Repository, doi:10.24432/C5KK69."),
]


def ch9(D):
    D.unnumbered_chapter("References", "_Toc_refs", toc_title="REFERENCES")
    D.toc[-1]["num"] = "9."
    D.add(para(run("The references follow the IEEE numeric style, numbered in the order in which they are first cited.", i=True, sz=22), jc="left", before=0, after=160))
    for n, r in enumerate(REFS, 1):
        D.add(f'<w:p><w:pPr><w:spacing w:before="0" w:after="100" w:line="276" w:lineRule="auto"/><w:ind w:left="567" w:hanging="567"/><w:jc w:val="both"/></w:pPr>'
              f'{run(f"[{n}]", sz=24)}{run("  ", sz=24)}{inline(r)}</w:p>')


def function_source(path: Path, name: str) -> list[str]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
            seg = ast.get_source_segment(src, node)
            assert seg, name
            return seg.split("\n")
    raise SystemExit(f"{name} not found in {path}")


def wrap_code(lines: list[str], width: int = 88) -> list[str]:
    out = []
    for ln in lines:
        if len(ln) <= width:
            out.append(ln)
            continue
        indent = len(ln) - len(ln.lstrip())
        out += textwrap.wrap(ln, width=width, subsequent_indent=" " * (indent + 8), break_long_words=True, break_on_hyphens=False, drop_whitespace=False)
    return out


def appendix(D, src: Path):
    D.unnumbered_chapter("Appendix A - Sample Code", "_Toc_appA", toc_title="APPENDIX A - SAMPLE CODE")
    D.toc[-1]["num"] = ""
    D.add(para(inline("The listings are copied from the repository by a script, so they are the code that produced the results. Long lines are wrapped for printing, "
                      "and file names are relative to the `realdata/src` directory.", sz=22, i=True), jc="both", before=0, after=160))
    items = [
        ("A.1  Case-centric flattening (ocel_io.py)", "ocel_io.py", ["flatten"]),
        ("A.2  Deficiency, convergence and divergence (ocel_io.py)", "ocel_io.py", ["flattening_stats"]),
        ("A.3  Rank agreement helpers (consequence.py)", "consequence.py", ["spearman", "topk_overlap", "variant_summary"]),
        ("A.4  Integrity check on a Zenodo download (fetch_sources.py)", "fetch_sources.py", ["fetch_zenodo"]),
        ("A.5  Safe extraction of archives (extract_archives.py)", "extract_archives.py", ["main"]),
    ]
    for title, fname, names in items:
        D.h4(title)
        lines = []
        for k, n in enumerate(names):
            if k:
                lines.append("")
            lines += function_source(src / fname, n)
        D.code(wrap_code(lines), sz=16)
