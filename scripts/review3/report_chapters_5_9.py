"""Chapters 5-9 and Appendix A of the Review 3 report. Result tables are generated from realdata/results at build time."""

from __future__ import annotations

import ast
import csv
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
    D.p("The study is built from seven modules, M1 to M7. Each module is a small Python script in the `realdata/src` directory, and each reads the output of the one before it. "
        "The architecture in Figure 4.1 shows how they connect.")

    D.h3("M1: Acquire and Verify")
    D.p("`fetch_sources.py` reads a manifest (`sources.json`) that lists each source, its record number, its licence and its expected files. "
        "For a Zenodo record, it asks the Zenodo interface for the file list, downloads each file, and compares the size and the MD5 checksum with the record. "
        "A mismatch deletes the file and stops the run. For OULAD, which comes from the UCI mirror and has no published checksum, we cap the download size and record the SHA-256. "
        "Every file gets a SHA-256 in a `SOURCE.md` file next to it. A stalled download resumes from the partial file with an HTTP Range request. This happened once during our run.")
    D.p("`extract_archives.py` extracts each archive into a new, empty directory next to it, and refuses any archive that contains an absolute path or a parent-relative (`..`) member path.")
    D.p("Table 5.1 lists the sources. The sizes of the logs are in Table 7.1.")
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
    D.p("Five of the logs are already in an OCEL format: Angular and Bundestag as JSON, Age of Empires as SQLite, Enron and Ethereum as parquet bundles. "
        "`convert_crop.py` and `convert_oulad.py` build OCEL 2.0 SQLite files for the two logs that are not. "
        "CROP becomes three object types (change, person, project) with events such as upload, comment, approve, merge and abandon. "
        "OULAD becomes four object types (student, enrollment, presentation, assessment) with events such as register, submit and unregister.")
    D.p("`ocel_io.py` loads every format into the same four pandas tables. It hashes personal identifiers with a salted hash (the Enron e-mail addresses and the CROP names), "
        "splits the Enron e-mail address type by role (sender, recipient, copied) so that each role can act as a case notion, and, for Ethereum, cuts a contiguous time window of 300,000 events. "
        "It also provides the flattening function used throughout, described next.")

    D.h3("M3: Distortion Metrics")
    D.p("A //case notion// is an object type chosen as the case. Flattening on type //T// produces one row for every distinct pair of an event and a T-object. "
        "This mirrors the flattening function of `pm4py`. Events with several T-objects are repeated, events with no T-object are dropped, and only event-level attributes survive. "
        "We call a case notion //analysed// when it covers at least 1,000 events. This gives 38 case notions over the seven logs. Table 5.2 defines the metrics.")
    D.table("Distortion metrics for a case notion T",
            ["Metric", "Definition", "How to read it"],
            [["Deficiency", "Share of events with no T-object", "Events a flat view drops"],
             ["Convergence share", "Share of covered events related to two or more T-objects", "Events copied into several cases"],
             ["Copies per event", "Flat rows divided by covered events", "Inflation of event counts (1.0 means none)"],
             ["Divergence share", "Share of (case, activity) pairs with two or more events whose other-object sets differ", "Repeated events that really belong to different things"],
             ["Nested child", "Another type U whose objects are almost exclusive to one case (95% or more), have their own lifecycle (two or more events) and a fan-out of at least 1.5 per case", "Items of an order, for example"],
             ["Cross-instance adjacency", "Among directly-follows pairs in cases with two or more nested children, the share whose two events concern disjoint children", "Events adjacent in the flat log but unrelated in the data"],
             ["Coupling", "For an ordered pair of types (T, U), the share of U-objects that touch two or more T-objects", "How much the cases share objects"],
             ["Variants per case", "Distinct activity sequences divided by cases", "How scattered the flat behaviour looks"]],
            [1.5, 3.4, 2.2], sz=18)
    D.p("These thresholds (95% exclusivity, fan-out of 1.5, 1,000 events) are our own choices. They are written at the top of `distortion.py` and `consequence.py`, and none was tuned to improve a result.")

    D.h3("M4: Consequence Analysis")
    D.p("Distortion metrics say how much a flat view differs. The consequence analysis asks what an analyst would read differently. "
        "The reference is the object-centric view: every event counted once, and the object-centric directly-follows relation, which is the union of consecutive-event pairs over the lifecycle of every object of every type. "
        "For each case notion we compare four outputs with that reference.")
    D.bullets([
        "**C1 Activity ranking.** Spearman rank correlation of the flat activity counts with (a) the counts of the whole process, each event once, and (b) the counts of the same covered events each counted once, which isolates the effect of duplication. We also report the share of activities visible at all.",
        "**C2 Directly-follows edges.** Duplication of event pairs (flat pairs divided by distinct pairs), rank agreement of edge frequencies with and without duplicates, the largest inflation among the ten most frequent reference edges, and, when nested children exist, the share of flat edge instances whose edge type never occurs inside any child (the spurious edge mass).",
        "**C3 Variants.** Distinct activity sequences, variants per case, and the share of cases covered by the ten most frequent variants.",
        "**C4 Entity ranking.** For every other object type with at least 30 objects, the rank correlation between the true number of events per object and the row count that a denormalised flat export of T would give, over the objects that appear in the export at all.",
    ])
    D.p("Two details keep the comparison fair. Events are coded by sorted event identifier, so that ties in time are always broken the same way. "
        "And the analysis separates //duplication// (the same event counted several times) from //narrowing// (events or activities that a case notion never sees), "
        "because a careful analyst can undo the first by de-duplicating on the event identifier, but nobody can recover the second from a flat log.")

    D.h3("M5: Predicate Engine (Appendix-Level)")
    D.p("From earlier work we keep a rule-based engine, `cooc.py` with `registry.py`. It evaluates eleven natural rules (for example, a change is merged only after an approval vote, or no submission after the assessment deadline) "
        "on native, flat and denormalised-flat views of CROP and OULAD. Since only two logs and eleven rules are involved, we do not draw conclusions from it and do not use it in the main results.")

    D.h3("M6: Validation")
    D.p("`sql_crosscheck.py` re-implements four CROP rules in plain SQL on the OCEL SQLite file, opened read-only. `check_consequence.py` compares the fast consequence code with a slow plain-Python version on a real slice of the Enron log. "
        "An independent recomputation from the raw OULAD CSV files checks the OULAD counts. Section 5.2 gives the results.")
    D.h3("M7: Summaries")
    D.p("`summarize_distortion.py`, `summarize_log_level.py` and `summarize_consequence.py` combine the per-log JSON files into the CSV and Markdown tables used in Chapter 7. `make study` runs the whole sequence.", jc="left")

    D.h2("Testing")
    D.p("We tested the project the way we would test someone else's work. Table 5.3 lists each check, what it proves and what we found.")
    D.table("Verification checks",
            ["Check", "What it proves", "Result"],
            [["Download integrity", "Zenodo files match the published size and MD5", "Verified for the Zenodo sources; SHA-256 recorded for every file, including OULAD"],
             ["Reproducibility", "Re-running gives the same outputs", "Tracked result files were byte-identical after a re-run (checked with Git)"],
             ["SQL cross-check", "The predicate code matches independent SQL", "4 of 4 CROP rules match exactly: 522, 19,109, 164 and 423 flagged changes"],
             ["Brute-force self-check", "The fast consequence code equals plain Python", "Directly-follows pairs identical on 4 case notions; entity ranking identical"],
             ["Independent recomputation", "OULAD counts match the raw CSV files", "15,348 enrolments with a late submission, 415 submissions after unregistration, 29 flagged by the stage-order rule: all exact"],
             ["Bugs found by our own checks", "Verification is not a formality", "Three bugs found and fixed (see below)"]],
            [1.7, 2.3, 3.0], sz=18)
    D.p("The checks found three bugs of our own, and we fixed all three before the results in this report were produced.")
    D.bullets([
        "**Duplicate events.** The CROP converter wrote duplicate event rows (about 17% of the event rows). They are removed.",
        "**A missed abandon form.** The converter did not recognise one phrasing of the Gerrit abandon message (\"Patch Set N: Abandoned\"). It does now.",
        "**Tie-breaking.** Events with the same timestamp could be ordered differently between two code paths. Events are now ordered by timestamp and then by event identifier.",
    ])
    D.p("What we did not do is just as important. We did not get a second person to label the findings independently. "
        "We reviewed a stratified sample of classified CROP comments by hand and found no further misclassification, but that reviewer was one of us, so it is not an independent label set. "
        "The converters are checked by us and not by a second team. The SQL cross-check tests the predicate code, not the CROP converter.")


# ------------------------------------------------------------------------------------------------ chapter 6
def ch6(D, demo_dir: Path):
    D.chapter_start("Project Demonstration")
    D.p("The live demonstration runs five commands from the `realdata` directory. We ran them for this report and stored the output files under `docs/review-3/demo/`, "
        "so the same text can be shown if the network or the laptop misbehaves on the day. Table 6.1 lists the steps and the measured times.")
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
    D.p("The manifest lists eight sources. All of them are already on disk with a `SOURCE.md` file, so the script skips them. On a clean machine the same command downloads about 350 MB.")
    D.h2("Step 2: Run the self-check")
    show("Command: .venv/bin/python -I src/check_consequence.py", "2_check.txt")
    D.p("The fast consequence code and a plain-Python version agree on a real Enron slice: the directly-follows pairs are identical for four case notions, and the entity ranking is identical too.")
    D.h2("Step 3: Distortion of the Enron log")
    show("Command: .venv/bin/python -I src/distortion.py enron", "3_distortion.txt")
    D.p("Four case notions are flattened: the three e-mail roles and the message identifier. Taking the copied-in recipients as the case (EMAILADDRESS:CC) drops 77.8% of the events and copies the rest 2.11 times on average, "
        "while the message identifier drops 40.1% and copies nothing. The coupling lines show how entangled the cases are: 81% of the \"to\" addresses take part in events that belong to two or more different \"cc\" cases (6.4 cases on average).")
    D.h2("Step 4: Consequences for the Enron log")
    show("Command: .venv/bin/python -I src/consequence.py enron", "4_consequence.txt")
    D.p("Each line is one case notion. For the copied-recipient case notion, only 77.8% of the activities are visible, and the activity ranking agrees with the whole process at a rank correlation of 0.87, "
        "although it is exactly 1.0 when only the effect of duplication is measured. In other words, almost all of that gap is narrowing, not duplication.")
    D.h2("Step 5: The cross-log summary")
    D.h4("Command: head -4 results/consequence_by_log.md")
    D.p("The command prints the Markdown table that has one row per log. Its lines are too wide for a printed page, so we do not copy them here. "
        "The saved output is in `docs/review-3/demo/5_table.txt`, and Table 7.3 in Chapter 7 shows the same numbers, which Chapter 7 then discusses.")
    D.p("The whole study can be re-run with `make study`. When we ran it for this report, it finished without error in 5 minutes 11 seconds and left every tracked result file unchanged (verified with Git).")


# ------------------------------------------------------------------------------------------------ chapter 7
def f(x, nd=2):
    return "-" if x in (None, "") else f"{float(x):.{nd}f}"


def ch7(D, res: Path):
    L = read_rows(res / "log_level_summary.csv")
    C = read_rows(res / "consequence_by_log.csv")
    N = read_all(res / "consequence_by_notion.csv")
    D.chapter_start("Result and Discussion")
    D.p("All numbers in this chapter are generated from the files in `realdata/results` and can be regenerated with `make study`. "
        "The results are measurements on seven real public logs. They do not describe the capstone portal.")

    D.h2("The Seven Logs")
    D.table("Profile of the seven logs",
            ["Log", "Domain", "Events", "Objects", "Object types", "Objects per event", "Analysed case notions"],
            [[LABEL[k], DOMAIN[k], f"{int(L[k]['events']):,}", f"{int(L[k]['objects']):,}", L[k]["types"], f(L[k]["objects_per_event"], 1), L[k]["case_notions_covering_ge1000_events"]] for k in ORDER],
            [1.7, 1.3, 0.9, 0.9, 0.8, 0.9, 0.9], sz=18, align=["left", "left", "right", "right", "center", "right", "center"])
    D.p("The logs span code review, education, legislation, e-mail, blockchain and game play. Together they give 38 analysed case notions. "
        "The Ethereum figures are for a contiguous window of 300,000 events of a log with 3.2 million.")

    D.h2("Distortion by Flattening")
    D.table("Flattening distortion per log (analysed case notions)",
            ["Log", "Regime", "Median share of events dropped", "Median copies per event", "Largest copies per event", "Notions with over 5% duplication", "Type pairs sharing 50% or more"],
            [[LABEL[k], REGIME[k], f"{100 * float(L[k]['median_deficiency']):.1f}%", f(L[k]["median_copies_per_event"]), f(L[k]["max_copies_per_event"]), f"{L[k]['notions_with_event_duplication_gt5pct']} of {L[k]['case_notions_covering_ge1000_events']}",
              f"{L[k]['pairs_with_ge50pct_shared_objects']} of {L[k]['type_pairs']}"] for k in ORDER],
            [1.5, 1.0, 1.0, 0.9, 0.9, 1.0, 1.0], sz=17, align=["left", "left", "right", "right", "right", "center", "center"])
    D.p("The logs fall into three groups, shown in Figure 7.1.")
    D.bullets([
        "**Star logs (CROP and OULAD).** Every event touches exactly one object of each type, so flattening copies nothing (1.00 copies per event) and, in the median, drops nothing. On these two measures the distortion is zero.",
        "**Partitioned logs (Bundestag, Age of Empires II, Ethereum).** Little is copied (at most 1.27, 1.76 and 1.09 copies per event), but different object types cover different parts of the log. One case notion drops about 69% to 91% of the events in the median.",
        "**Fan-out logs (Angular commits and Enron).** One event relates to many objects of the same type. The largest duplication is 81.65 copies per event in Angular (the branch case notion) and 2.11 in Enron.",
    ])
    D.figure("fig_regimes.png", "Duplication and dropped events for the seven logs, by regime", 5.6)
    D.p("Coupling is the other side of the story. Figure 7.2 shows the share of object-type pairs in which the objects of one type are shared across the cases of the other. "
        "In every log except the Bundestag and Age of Empires, at least half the type pairs share more than half of their objects. In Angular, both of the two pairs do.")
    D.figure("fig_coupling.png", "Object-type pairs that share more than half of their objects across cases", 5.4)

    D.h2("Consequences for Standard Outputs")
    D.table("Consequences of flattening per log",
            ["Log", "Notions", "Activities visible (median)", "Activity rank correlation, whole process (median / lowest)", "Lowest, duplication only", "Largest edge duplication", "Lowest entity-rank correlation"],
            [[LABEL[k], C[k]["notions"], f(C[k]["activity_visible_share_median"]), f"{f(C[k]['activity_rank_rho_all_median'])} / {f(C[k]['activity_rank_rho_all_min'])}", f(C[k]["activity_rank_rho_dup_only_min"]),
              f(C[k]["df_pair_duplication_max"]), f(C[k]["entity_rho_visible_min"])] for k in ORDER],
            [1.4, 0.7, 0.9, 1.5, 0.9, 0.9, 0.9], sz=16, align=["left", "center", "right", "center", "right", "right", "right"])
    dup_low = [(r["log"], r["case_type"], float(r["act_rank_rho_dup_only"])) for r in N if float(r["act_rank_rho_dup_only"]) < 0.95]
    narrow = sum(1 for r in N if float(r["act_visible_share"]) < 0.5)
    D.p("Three results stand out.")
    D.p(f"//Duplication alone rarely changes a ranking.// Comparing the activity ranking from flat rows with the ranking of the same events counted once, "
        f"only {len(dup_low)} of the {len(N)} case notions fall below a rank correlation of 0.95: Angular files ({dup_low[0][2]:.2f}) and the Enron \"to\" role ({dup_low[1][2]:.2f}). "
        "Where a log has no duplication (star logs), the correlation is exactly 1.0.")
    D.p(f"//Narrowing is the larger effect.// In {narrow} of the {len(N)} case notions the flat log shows fewer than half of the activities of the whole process. "
        "The activity rank correlation with the whole process has a median of only 0.17 in the Bundestag and 0.21 in Age of Empires II. "
        "A flat view in those logs is not a distorted picture of the process; it is a small piece of it.")
    D.figure("fig_rank_activity.png", "Activity ranking agreement: duplication alone versus the whole process", 5.6)
    D.p("//Careless counting can mislead.// Suppose an analyst ranks entities (for example, people) by counting the rows of a denormalised flat export. "
        "Among the entities that appear in the export, the worst case rank correlations with the true number of events per entity are 0.16 in Enron, -0.01 in Ethereum and -0.41 in Age of Empires II. "
        "An analyst who de-duplicates on the event identifier would avoid this, so the finding is about careless counting and not about an unavoidable loss.")
    D.figure("fig_rank_entity.png", "Entity ranking agreement from a denormalised flat export", 5.6)
    D.p("Directly-follows edges show a smaller but real effect. Angular has the largest duplication of event pairs (74 copies for the branch case notion). "
        "Where nested children exist, some flat edges join events that are adjacent in the flat log but unrelated in the data. The share of such spurious edges is at most 27.7% in Age of Empires II and 16.6% in OULAD.")
    D.figure("fig_spurious.png", "Spurious directly-follows edges, worst case notion per log", 5.4)

    D.h2("Discussion")
    D.p("Our starting guess was that flattening mainly duplicates events. The data says otherwise. Duplication is large in only two of the seven logs. "
        "The common problem is that one case notion sees only part of the process, and that problem is invisible in a flat log because nothing marks what is missing.")
    D.p("What does this mean for the capstone? We can only offer a hypothesis, not a result, because we have no portal data. "
        "The portal's documented audit log relates each action to one project and to the acting person. "
        "If the real data has that shape, then flattening on the project would copy few events, but it would hide how one guide's reviews are spread across many projects, and it would hide the people. "
        "That is the narrowing pattern, not the duplication pattern. The right next step is to test this on a de-identified portal log, and until then we make no claim about the portal.")
    D.h3("Threats to Validity")
    D.bullets([
        "**Seven logs from five domains.** The three regimes are descriptive; we do not claim they are exhaustive.",
        "**Our choices.** Case notions are object types (and roles for Enron). Thresholds for nested children and for the minimum case-notion size are our own and are written in the code.",
        "**A window of Ethereum.** The Ethereum results come from a contiguous window of 300,000 events.",
        "**A data-quality flag in Enron.** About 0.1% of the events (72) have timestamps before 1990, which is odd for a 1998 to 2002 corpus. We left them in.",
        "**Checks by us.** The independent implementations are independent of the code under test, not of the team. No second person labelled the findings.",
    ])

    D.h2("Cost Analysis")
    D.p("Cost here means money and effort to produce or reproduce the study. Table 7.4 summarises it.")
    D.table("Cost of producing and reproducing the study",
            ["Item", "Producing the study", "Reproducing it"],
            [["Data", "Nil (open data, CC BY 4.0)", "About 350 MB download for the core set"],
             ["Software", "Nil (open-source libraries; `pm4py` is AGPL-3.0)", "Python 3.14 and the pinned packages in `requirements.txt`"],
             ["Hardware", "A laptop the team already owned (8 GiB memory)", "Any laptop with 8 GiB of memory or more"],
             ["Cloud or paid services", "None", "None"],
             ["Run time", "Seconds to minutes per log", "About 4 to 10 seconds for the Enron log; `make study` for all seven logs took 5 minutes 11 seconds"]],
            [1.4, 3.0, 2.6], sz=18)
    D.p("The honest cost is the team's time and the care that went into verification. The money cost is nil.")


# ------------------------------------------------------------------------------------------------ chapter 8
def ch8(D):
    D.chapter_start("Conclusion")
    D.p("We set out to study capstone review processes with OCEL 2.0. Portal logs were not available, so the project became two things: a documented OCEL 2.0 design of the capstone lifecycle, "
        "and a measurement of what flattening does on seven real public logs.")
    D.p("Our conclusions are these.")
    D.bullets([
        "**A reproducible, checked pipeline exists.** It downloads and verifies seven public logs, converts two of them to OCEL 2.0, computes distortion metrics for 38 case notions, and compares standard outputs between flat and object-centric views. Independent SQL, brute-force and recomputation checks agree with it, and they found three bugs of our own, which we fixed.",
        "**Flattening does not mainly duplicate events.** Duplication is large only in the fan-out logs (up to 81.65 copies of an event in Angular). Only 2 of 38 case notions fall below a rank correlation of 0.95 because of duplication alone.",
        "**The larger effect is narrowing.** In 20 of 38 case notions the flat log shows fewer than half of the process's activities, and in the partitioned logs one case notion drops 69% to 91% of the events.",
        "**Careless counting from a flat export can mislead badly.** Worst-case entity rankings reach a rank correlation of 0.16 (Enron), -0.01 (Ethereum) and -0.41 (Age of Empires II).",
        "**The capstone model is a design.** We could not test it on portal data, and we do not claim anything about how real capstone teams behave.",
    ])
    D.h2("Limitations")
    D.p("We have seven logs from five domains, one of them a window. The thresholds are ours. The checks are independent of the code under test but not of the team, and no second person has labelled the findings. "
        "The predicate engine covers only eleven rules on two logs and is not used for any conclusion.")
    D.h2("Future Work")
    D.bullets([
        "Get independent two-rater labelling of the real-data findings.",
        "Compare process-discovery quality and predictive monitoring between flat and object-centric logs.",
        "Add two or three more real logs, for example BPI 2019.",
        "Build a portal adapter from the audit log to OCEL 2.0, once de-identified logs are approved.",
        "Finish the journal manuscript. A draft is in preparation; it has not been submitted, and no venue has been chosen.",
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
    D.add(para(inline("The listings are copied from the repository by script, so that they are the code that produced the results. Long lines are wrapped for printing. "
                      "File names are relative to the `realdata/src` directory.", sz=22, i=True), jc="both", before=0, after=160))
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
