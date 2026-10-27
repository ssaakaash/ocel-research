"""Chapters 1-4 of the Review 3 report. Every number here comes from realdata/results or from the repository docs."""

from __future__ import annotations


def ch1(D):
    D.chapter_start("Introduction")
    D.h2("Background")
    D.p("Consider what happens when a student leader submits a capstone report. That single event concerns the project, the team, three students, "
        "the guide who will verify it and the report version being submitted. A process-mining tool, however, needs to know which one of these is the case.")
    D.p("This question motivates the project. Classical process mining starts from an event log in which every event has a case identifier, an activity name and a timestamp, "
        "and the techniques built on top of it (discovery, conformance checking, bottleneck analysis) assume that each event belongs to exactly one case.")
    D.p("If the project is chosen as the case, each project's history stays together, but the guide's workload across all projects disappears. If the student is chosen, the same submission appears three times, "
        "once per team member. A useful comparison is a group photograph. A flat view cuts one person out of the picture. Every person can be cut out in turn, "
        "but the resulting set of cut-outs no longer shows who was standing next to whom.")
    D.p("The literature names these distortions. When one event is copied into several cases, the result is //convergence//. When repeated events that belong to different objects of another type are merged into one case, "
        "the result is //divergence// [1]. Events that have no object of the chosen type are dropped from the flat log altogether, which is called //deficiency//.")
    D.p("Object-centric event logs avoid this choice. One event can refer to any number of objects, each with a type, and objects can also be linked to each other. "
        "OCEL 2.0 [2] standardises this structure, with JSON, XML and SQLite formats, a qualifier on every link, and object attributes that can change over time.")
    D.p("Several studies show why this structure matters. Keeping the object graph improves machine-learning tasks on process data compared with flattened features [3], "
        "and Adams and van der Aalst [4] address convergence, divergence and deficiency together. One-to-many links produced false directly-follows relations in a food-company case study [5], "
        "and object-centric data has quality problems of its own [6]. In education, Miri et al. [7] converted Moodle activity into OCEL and found that group and resource links remain invisible in a student-centric log.")
    D.p("What we could not find was a study that measures these effects across several real logs. The problem is widely acknowledged, but its size has not been reported. "
        "Suitable public data does exist: the Open University Learning Analytics Dataset (OULAD) [8] covers students, courses and assessments, and CROP [9] links Gerrit code reviews to code changes, a process closely related to report review.")
    D.p("A capstone has the same structure. Hassani et al. [10] describe a department supervising more than 250 final-year computing projects, and Premchaiswadi and Porouhan [11] mined an online peer-review process "
        "and found bottlenecks and rule violations in reviewer handling. The Educational Capstone Portal, whose architecture is documented in our project repository, handles registration, team formation, "
        "report compilation, three review stages, faculty decisions and scoring, and it writes an audit-log row for every state change. Its process is therefore strongly object-centric.")
    D.p("We set out to study that process directly, but portal logs could not be obtained, and we found no public capstone or thesis-management event log. "
        "We therefore narrowed what we claim. The capstone is presented as a documented OCEL 2.0 design, and the measurements are made on seven real public logs [16]. "
        "This report keeps the two parts clearly separate.")

    D.h2("Motivations")
    D.p("First, flattening happens without notice. Tools apply it by default and rarely report how many events were copied, dropped or merged.")
    D.p("Second, the evidence is thin. Convergence and divergence are usually explained with small examples or a single case study, and we found no work that reports how often and how strongly they occur across several real logs.")
    D.p("Third, capstones are coordination work. The questions that matter in practice (whether one guide is overloaded, or which team resubmits repeatedly) cut across cases, so a case-centric view does not fit them.")
    D.p("Fourth, our claims are limited to the data we can access. Portal data is not available to us, so a re-runnable measurement on public logs is the strongest evidence we can provide.")

    D.h2("Scope of the Project")
    D.p("Table 1.1 states what the project covers and what it does not, so that its limits are explicit from the start.")
    D.table("Scope of the project",
            ["In scope", "Out of scope"],
            [["An OCEL 2.0 model of the capstone lifecycle, designed from the portal documentation", "Any claim about how real capstone teams behave; no portal data was used"],
             ["A re-runnable pipeline: download, verify, convert, load, analyse", "Predictive monitoring on flat versus object-centric logs"],
             ["Flattening distortion for 38 case notions on seven real public logs", "Independent human labelling of the findings by a second rater"],
             ["A consequence analysis: activity rankings, directly-follows edges, variants, entity rankings and discovered models, flat versus object-centric", "Integrating a portal adapter; this is future work"],
             ["Independent checks of our own code, and a documented list of bugs they found", "Synthetic or simulated data of any kind"]],
            [1, 1])
    D.p("Two further points apply. A rule-based engine from our earlier work is kept at appendix level, since eleven rules on two logs cannot support a conclusion. "
        "In addition, a Moodle log from the University of Cádiz was downloaded as an eighth source but is not used in any result.")
    D.p("The report is organised as follows. Chapter 2 covers the literature and the plan, Chapter 3 the requirements and feasibility, Chapter 4 the design, Chapter 5 the modules and testing, Chapter 6 the demonstration, "
        "Chapter 7 the results and cost, Chapter 8 the conclusion and Chapter 9 the references. Appendix A contains sample code.")


def ch2(D):
    D.chapter_start("Project Description and Goals")
    D.h2("Literature Review")
    D.p("The literature falls into four groups: the flattening problem itself, the OCEL format, what flattening does to results and to data quality, and the education and capstone papers. "
        "Table 2.1 sums up the ones that matter most for our questions. The full list is in Chapter 9.")
    D.table("Summary of the reviewed literature",
            ["Ref.", "Objective", "Method", "Strength and limitation", "Finding"],
            [["van der Aalst (2019) [1]", "Name the problems of one-case-per-event logs", "Conceptual analysis with worked examples", "Defines convergence and divergence. No measurement on real logs", "Flattening copies events across cases or mis-orders them"],
             ["Berti et al. (2024) [2]", "A standard exchange format for object-centric data", "OCEL 2.0 specification: JSON, XML, SQLite, qualifiers, O2O links", "Expressive, with tool support. Extraction still needs domain decisions", "One event can relate to many typed objects"],
             ["Adams, Park, van der Aalst (2023) [3]", "Keep object-centric graph structure for machine learning", "Compare graph encodings with flattened features on predictive tasks", "Shows the value of structure. Focus is prediction, not analysis outputs", "Structure-preserving encodings are favoured over flattening"],
             ["Waibel et al. (2022) [5]", "Causal structure from relational data", "Causal event graph on one food-company case", "Avoids false edges. Only one case study", "One-to-many and many-to-many links give spurious directly-follows relations"],
             ["Kabierski et al. (2026) [6]", "Classify quality issues in object-centric data", "Classification checked on real logs and practitioner interviews", "Practitioner-validated. Classifies issues but gives no distortion rates", "Object-centric data has quality problems of its own, e.g. wrong object relations"],
             ["Miri et al. (2026) [7]", "Object-centric educational process mining", "Moodle to OCEL conversion, real course case study", "First educational use. One course, not a transactional lifecycle", "Group and resource links are invisible in student-centric logs"],
             ["Premchaiswadi, Porouhan (2015) [11]", "Mine a peer-review process in an online system", "Event log from review handling; discovery and conformance", "Real review workflow. One case notion", "Bottlenecks and rule violations found in reviewer handling"],
             ["Hassani et al. (2018) [10]", "Manage more than 250 computing final-year projects", "Case study of supervision, panels and rubrics", "Real capstone practice. No event data", "Capstones need coordinated supervision, submission and assessment"]],
            [1.25, 1.35, 1.5, 1.6, 1.5], sz=17)
    D.p("On the flattening problem itself, van der Aalst [1] explained why one-case-per-event logs misrepresent processes with several interacting entities, and Adams and van der Aalst [4] "
        "went on to cover convergence, divergence and deficiency together. Both papers are conceptual, and neither reports how often these effects occur in real data.")
    D.p("OCEL 2.0 [2] is the format we build on. It stores events, objects, event-to-object (E2O) links and object-to-object (O2O) links, each with qualifiers, in JSON, XML or SQLite. "
        "Our own converters write the SQLite form, and we read the JSON and XML forms of the public logs.")
    D.p("On consequences, Waibel et al. [5] used a causal event graph to show that one-to-many links produce false directly-follows edges, but only on one company's data. "
        "Kabierski et al. [6] classified the quality issues of object-centric data; they describe the kinds of problems but do not count them. Adams et al. [3] showed that keeping the object graph helps predictive tasks.")
    D.p("In education, Miri et al. [7] is the closest related work, since they applied object-centric mining to Moodle data. This project is therefore not the first use of OCEL in education. "
        "Premchaiswadi and Porouhan [11] mined an online peer-review process with a single case notion, and Hassani et al. [10] describe how a department supervises a large number of final-year projects, with no event data.")

    D.h2("Research Gap")
    D.p("Taken together, the reviewed work leaves three gaps.")
    D.p("First, flattening problems are named but not measured. Convergence and divergence appear in small or single-case examples, and most object-centric evidence we found uses simulated logs.")
    D.p("Second, work on education and capstones relies on learning-platform data. Object-centric educational mining uses Moodle activity. "
        "A review lifecycle with submit, review, reject, resubmit and score has no public object-centric dataset.")
    D.p("Third, capstone portal logs are not available. Searches of Zenodo, 4TU and the web found no public capstone or thesis-management event log, so we cannot test the capstone claim directly.")
    D.p("Our approach is therefore to measure flattening on real review-like and multi-entity logs, to give the capstone an OCEL 2.0 model, and to state the limits explicitly.")

    D.h2("Objectives")
    D.p("The project has five objectives, in the order we worked on them.")
    D.bullets([
        "O1. Model the capstone lifecycle as OCEL 2.0 from the documented portal behaviour.",
        "O2. Build a reproducible pipeline: download, verify, convert, load and analyse.",
        "O3. Measure flattening distortion on seven real logs without hand-picked rules.",
        "O4. Compare standard outputs (activity rankings, directly-follows edges, variants, entity counts and discovered process models) between flat and object-centric views.",
        "O5. Verify every result with independent checks and keep the code re-runnable.",
    ])
    D.p("The work touches two of the United Nations Sustainable Development Goals: Goal 4, Quality Education, since it concerns how academic review processes are recorded and understood, "
        "and Goal 9, Industry, Innovation and Infrastructure, since it adds open tooling for object-centric process data. "
        "On the Technology Readiness Level scale we put the pipeline at TRL 4 (validated in the laboratory, on seven public logs) and portal integration at TRL 2 to 3. Those levels are our own estimate.")

    D.h2("Problem Statement")
    D.p("We have an object-centric event log with several object types, and we pick one type as the case notion. Two questions follow. "
        "How much does the flat log differ from the object-centric one, that is, how many events are copied, dropped or merged? "
        "And do those differences change what an analyst reads from the standard outputs: activity rankings, directly-follows edges, process variants, entity rankings and discovered models? "
        "Both questions must be answered on real data only, with checks that do not depend on our own code, and the capstone lifecycle must be specified in OCEL 2.0 even though no portal data exists.")

    D.h2("Project Plan")
    D.p("Figure 2.1 shows the project calendar. At Review 2 we presented a prototype that was evaluated on synthetic data. The team then decided to use real data only, "
        "so that prototype and its results are excluded from this work, and the plan below reflects the work done after that decision.")
    D.figure("fig_timeline.png", "Project calendar, August to December 2026 (grey bars are not part of the delivered work)", 5.9)
    D.table("Work packages and status",
            ["Work package", "Content", "Status"],
            [["WP1", "Literature review and scope", "Completed"],
             ["WP2", "Platform study and OCEL 2.0 schema of the capstone lifecycle", "Completed (design only)"],
             ["WP3", "Re-scope to real data only; locate and download public logs", "Completed"],
             ["WP4", "Convert CROP and OULAD to OCEL 2.0; profile all seven logs", "Completed"],
             ["WP5", "Distortion metrics and consequence analysis", "Completed"],
             ["WP6", "Independent verification, report and presentation", "Completed"],
             ["WP7", "Process-discovery comparison, bootstrap intervals and full-log verification", "Completed"],
             ["WP8", "Journal manuscript", "Submitted to the Journal of Intelligent Information Systems (Springer), October 2026; under review"],
             ["WP9", "Independent labelling of the findings", "Planned"]],
            [0.9, 4.2, 2.6])


def ch3(D):
    D.chapter_start("Technical Specification")
    D.h2("Requirements")
    D.h3("Functional")
    D.p("Table 3.1 lists the functional requirements and the module that covers each one. Chapter 5 describes the modules.")
    D.table("Functional requirements",
            ["ID", "The system shall", "Module"],
            [["FR1", "Download datasets from a manifest; check size and MD5 where the publisher provides them, and record a SHA-256 for every file", "M1"],
             ["FR2", "Extract archives without trusting member paths", "M1"],
             ["FR3", "Convert Gerrit code reviews (CROP) and OULAD into OCEL 2.0 SQLite", "M2"],
             ["FR4", "Load OCEL from SQLite, JSON, XML and bundled formats, with hashed identifiers for personal data", "M2"],
             ["FR5", "Compute flattening distortion for every object type of every log", "M3"],
             ["FR6", "Compare flat and object-centric outputs: rankings, edges, variants and entities", "M4"],
             ["FR7", "Validate results with independent implementations", "M6"],
             ["FR8", "Export CSV, JSON and Markdown tables; re-run the whole study with one command", "M7"]],
            [0.6, 5.6, 0.8], align=["center", "left", "center"])
    D.h3("Non-Functional")
    D.table("Non-functional requirements",
            ["ID", "Requirement", "How we meet or check it"],
            [["NFR1", "Reproducibility: the same input gives the same bytes", "Tracked result files were byte-identical after a re-run"],
             ["NFR2", "Privacy: personal identifiers are not published", "E-mail addresses and names are hashed on load; no VIT student data is used"],
             ["NFR3", "Resource limit: runs on an ordinary laptop", "Developed on an 8 GiB machine; the Ethereum log is analysed as a 300,000-event window"],
             ["NFR4", "Licensing: only openly licensed data", "All seven logs are CC BY 4.0; the licence is recorded per source"],
             ["NFR5", "Integrity and safety of data handling", "Size and MD5 checked against the Zenodo record; SHA-256 recorded for all files; archives with unsafe member paths rejected"],
             ["NFR6", "Transparency of limits", "Every result table states what was and was not checked"]],
            [0.7, 3.0, 3.3])

    D.h2("Feasibility Study")
    D.h3("Technical Feasibility")
    D.p("The pipeline is written in Python with open-source libraries and runs on a single laptop. The only memory constraint was the Ethereum log, whose 3.2 million events do not fit in 8 GiB of memory, "
        "so we analyse a contiguous window of 300,000 events and state this wherever that log appears. For Enron, the distortion analysis took about 9.5 seconds and the consequence analysis about 4. "
        "Run time was not a risk; correctness was, which is why Chapter 5 devotes most of its space to verification.")
    D.h3("Economic Feasibility")
    D.p("No data, software or cloud time was purchased. Table 3.3 lists the items. The only cost that cannot be quantified is the team's own time.")
    D.table("Cost items",
            ["Item", "Source", "Incremental cost"],
            [["Datasets (seven logs)", "Zenodo and UCI repositories, CC BY 4.0", "Nil"],
             ["Analysis software", "Python and open-source libraries (see Section 3.3.2)", "Nil"],
             ["Hardware", "A laptop the team already owned", "Nil"],
             ["Storage", "About 1.3 GB of downloaded and extracted files and 132 MB of derived OCEL files", "Nil"],
             ["Cloud or paid services", "None used", "Nil"]],
            [2.2, 3.4, 1.4])
    D.p("One licensing point needs attention. The `pm4py` library is released under AGPL-3.0, and we use it as a reference implementation of flattening and for process discovery. "
        "The code is public on GitHub and is released under AGPL-3.0, which is compatible with `pm4py`.")
    D.h3("Social Feasibility")
    D.p("Two logs contain data about people. Enron has real e-mail addresses, and CROP has developer names that its authors had already pseudonymised. "
        "We hash identifiers again when a log loads and never print raw values. No VIT student, guide or portal record was used. "
        "The method lets anyone who analyses multi-entity workflows, including academic review, see in advance what a flat view will hide.")

    D.h2("System Specification")
    D.h3("Hardware Specification")
    D.table("Hardware used",
            ["Item", "Specification"],
            [["Machine", "Apple silicon laptop (arm64)"],
             ["Memory", "8 GiB"],
             ["Storage used", "1.3 GB raw (downloaded and extracted), 132 MB derived OCEL files; the one-time download is about 350 MB"]],
            [1.5, 5.0])
    D.h3("Software Specification")
    D.table("Software used",
            ["Component", "Version", "Use"],
            [["Python", "3.14.5", "All analysis code"],
             ["pandas, NumPy, SciPy", "3.1.0, 2.5.4, 1.18.1", "Tables, vectorised metrics, Spearman correlation"],
             ["lxml", "6.1.3", "XML OCEL loading"],
             ["pm4py", "2.7.23.11", "Reference flattening implementation (AGPL-3.0)"],
             ["DuckDB", "2.0.0", "Reads the parquet OCEL bundles (Enron, Ethereum) without extra libraries"],
             ["Matplotlib", "3.11.2", "Figures"],
             ["SQLite", "3.54.0", "OCEL 2.0 storage and the independent SQL cross-check"],
             ["macOS, Git, Make", "-", "Operating system, version control, one-command re-run"]],
            [2.2, 1.8, 3.0])


def ch4(D):
    D.chapter_start("Design Approach and Details")
    D.h2("System Architecture")
    D.p("Figure 4.1 reads from left to right. The seven public logs enter on the left. The first stage downloads each file, checks it against the publisher's record where one exists, and records a SHA-256 checksum. "
        "A second stage extracts archives safely. Then the conversion stage turns CROP and OULAD into OCEL 2.0, and every log ends up in the same four tables: events, objects, event-to-object links and object-to-object links.")
    D.figure("fig_architecture.png", "System architecture of the flattening study", 6.3)
    D.p("Three engines read those tables. The distortion engine computes deficiency, convergence, divergence and coupling for each case notion. The consequence engine compares flat and object-centric outputs. "
        "The rule-based engine is the appendix-level part. A validation stage re-implements the key computations independently, and all results are written as CSV, JSON and Markdown files from which the report and the paper are produced. "
        "The dashed box at the top has not been built. It marks where an adapter for the portal's audit log would connect, should de-identified logs be approved.")

    D.h2("Design")
    D.h3("Data Flow Diagram")
    D.p("Figure 4.2 is the level-0 diagram, with one process and two external entities. Public data publishers supply dataset archives and licences. "
        "The researchers and the guide supply run commands and settings, and receive tables, figures and validation status.")
    D.figure("fig_dfd0.png", "Data flow diagram, level 0", 5.6)
    D.p("Figure 4.3 decomposes that process into six sub-processes. Process 1.0 acquires and verifies archives into store D1. Process 2.0 extracts and converts them into the OCEL logs of store D2. "
        "Processes 3.0 (distortion metrics) and 4.0 (consequence analysis) read D2 and write the metric tables of store D3. Process 5.0 validates, and process 6.0 summarises the results for the researchers.")
    D.figure("fig_dfd1.png", "Data flow diagram, level 1", 6.2)
    D.h3("Use Case Diagram")
    D.p("Figure 4.4 has two actors. The researcher (the team) downloads and verifies datasets, converts a source to OCEL 2.0, computes distortion metrics, runs the consequence analysis, validates against independent code and exports tables. "
        "The guide or panel reviews the results and approves them.")
    D.figure("fig_usecase.png", "Use case diagram", 5.6)
    D.h3("Class Diagram")
    D.p("Figure 4.5 shows the main data structures. `Ocel` holds the four tables of a loaded log. `Prepared` wraps an `Ocel` with integer-coded arrays, which makes the rankings and directly-follows counts fast to compute. "
        "`View` and `Predicate` belong to the rule-based engine, where a predicate is evaluated on a view of the log (native, flat or denormalised flat). "
        "Note that in the code the loader and the registry are modules of functions, not classes; they are drawn as classes to make their roles clear.")
    D.figure("fig_class.png", "Class diagram of the main structures", 6.0)
    D.h3("Sequence Diagram")
    D.p("Figure 4.6 follows one full run. The researcher starts the download, which verifies and records each file. Conversion writes OCEL 2.0 SQLite. "
        "The distortion engine asks the loader for an `Ocel` and writes its JSON results, and the consequence engine does the same. The self-check recomputes the directly-follows pairs and the entity ranking in plain Python, and the summaries come last.")
    D.figure("fig_sequence.png", "Sequence diagram of one end-to-end run", 6.2)

    D.h2("OCEL 2.0 Model of the Capstone Lifecycle (Design Only)")
    D.p("This section describes the model we designed for the portal, and it is a design, not a result. We derived it from the portal's documentation (the audit-trail, submission-system and scoring-system documents in the repository), "
        "and it has not been populated with portal data because none is available.")
    D.table("Object types of the capstone model",
            ["Object type", "Meaning", "Example relations (qualifiers)"],
            [["Student", "A team member; the leader may submit", "member-of (team)"],
             ["Team", "Group executing one project", "executes (project)"],
             ["Project", "The capstone project", "has-report, guides"],
             ["Faculty (guide)", "Guide who approves ideas, opens reviews and decides", "guides (project), reviews (stage)"],
             ["Report", "The report for a project", "has-version"],
             ["Report version", "One compiled version; incremented on each rejection", "has-score"],
             ["Review stage", "R1, R2 or R3", "at-stage"],
             ["Score", "Similarity and AI percentages; written once, then locked", "has-score (from version)"]],
            [1.4, 3.2, 2.4])
    D.figure("fig_capstone_schema.png", "Object types, relations and events of the capstone lifecycle", 6.0)
    D.p("The portal writes an audit-log row for every state transition, and the documented action vocabulary gives eight event types: `PROJECT_CREATED`, `COMPILATION_STARTED`, `COMPILATION_SUCCESS`, `COMPILATION_FAILED`, "
        "`STUDENT_SUBMITTED`, `FACULTY_STARTED_VERIFICATION`, `FACULTY_ACCEPTED` and `FACULTY_REJECTED`. Each row carries a project identifier, the acting student or faculty member and a timestamp. "
        "In the model, an event relates to its project, to the acting student or faculty member, and, through joins on the project, to the team, the report version and the stage.", jc="left")
    D.p("A few documented facts shape the model. A score is written once and then locked. A rejection uses up one of three attempts and increments the report version. "
        "Compilation failures are free retries and do not use an attempt. The documentation lists the automatic move from stage R1 to R2 to R3 as a known gap, "
        "so the stage relation is part of the design, but the current system does not fully populate it.")
