"""Chapters 1-4 of the Review 3 report. Every number here comes from realdata/results or from the repository docs."""

from __future__ import annotations


def ch1(D):
    D.chapter_start("Introduction")
    D.h2("Background")
    D.p("Process mining starts from an event log. In its simplest form every event has three things: a case identifier, an activity name and a timestamp. "
        "The usual toolbox (discovering a process model, checking conformance, finding bottlenecks) rests on one assumption: every event belongs to exactly one case.")
    D.p("Real processes rarely behave that way. Take a capstone review. When a student leader submits a report, that one event concerns the project, the team, three students, "
        "the guide who will verify it and the report version being submitted. If we choose the project as the case, the project's story stays together but the guide's workload across many projects disappears. "
        "If we choose the student, the same submission is written down three times, once per team member. A group photograph is a fair picture of it. "
        "A flat view cuts one person out of the photo. We can make a cut-out for every person, but the pile of cut-outs never tells us who stood next to whom.")
    D.p("The literature gives the damage names. When one event is copied into several cases the log shows //convergence//. When events of the same activity inside one case really belong to different other objects, "
        "the log shows //divergence// [1]. Events that have no object of the chosen type vanish from the flat log, which is called //deficiency//; the three issues are treated together in [4].")
    D.p("Object-centric event logs avoid the choice. One event can be related to any number of objects, each with a type, and objects can be related to each other. "
        "The OCEL 2.0 specification [2] turns this idea into a standard with JSON, XML and SQLite formats, a qualifier on every link, and object attributes that may change over time. "
        "Recent papers show why the structure matters. Keeping the object graph helps machine-learning tasks on process data more than flattened features do [3]. "
        "One-to-many links create spurious directly-follows relations in a real food-company case study [5]. Object-centric data also has quality problems of its own [6]. "
        "In education, Miri et al. [7] converted Moodle activity into OCEL and found that group and resource links stay invisible in a student-centric log. "
        "What we could not find is a study that counts how large these effects are across several real logs.")
    D.p("Public data now makes such a count possible. The Open University Learning Analytics Dataset (OULAD) [8] covers students, courses and assessments. "
        "CROP [9] links Gerrit code reviews to code changes, a close cousin of a report-review workflow: submit, review, revise, accept.")
    D.p("The capstone itself has the same shape. Hassani et al. [10] describe a department that supervises more than 250 final-year computing projects, "
        "and Premchaiswadi and Porouhan [11] mined a peer-review process and found bottlenecks and rule violations in reviewer handling. "
        "The Educational Capstone Portal, a capstone management system whose architecture is documented in our project repository, handles registration, team formation, report compilation, "
        "three review stages, faculty decisions and scoring, and it writes an audit-log row for every state change. That is a naturally object-centric process.")
    D.p("We started this project to study exactly that process. We could not obtain portal logs, and we found no public capstone or thesis-management event log. "
        "So we changed what we claim. We kept the capstone as a documented OCEL 2.0 design, and we measured flattening on seven real public logs [12]. "
        "This report describes both parts and is careful to say which one is which.")

    D.h2("Motivations")
    D.bullets([
        "**Flattening is routine and quiet.** Tools flatten by default and rarely tell the analyst how much was copied, dropped or mixed up.",
        "**The evidence is thin.** Convergence and divergence are explained with toy examples or single case studies. We found no study that reports how often and how badly they occur on several real logs.",
        "**Capstones are coordination work.** The questions that matter (is one guide overloaded, which team keeps resubmitting) cut across cases, and a case-centric view is the wrong shape for them.",
        "**We can only be honest about what we can reach.** Portal data is not available to us, so a careful, re-runnable measurement on public logs is the strongest evidence we can really produce.",
    ])

    D.h2("Scope of the Project")
    D.p("Table 1.1 states what the project covers and what it does not. We would rather list the limits ourselves.")
    D.table("Scope of the project",
            ["In scope", "Out of scope"],
            [["An OCEL 2.0 model of the capstone lifecycle, designed from the portal documentation", "Any claim about how real capstone teams behave; no portal data was used"],
             ["A re-runnable pipeline: download, verify, convert, load, analyse", "Process-discovery quality and predictive monitoring on flat versus object-centric logs"],
             ["Flattening distortion for 38 case notions on seven real public logs", "Independent human labelling of the findings by a second rater"],
             ["A consequence analysis: activity rankings, directly-follows edges, variants and entity rankings, flat versus object-centric", "Integrating a portal adapter; this is future work"],
             ["Independent checks of our own code, and a documented list of bugs they found", "Synthetic or simulated data of any kind"]],
            [1, 1])
    D.p("Two further points belong here. A rule-based engine from our earlier work, which tests eleven natural predicates on CROP and OULAD, is kept only as an appendix-level component, "
        "because eleven rules on two logs are too few to conclude anything. And an eighth source, a Moodle event log from the University of Cádiz, was downloaded but is not used in any result here.")
    D.p("Chapter 2 reviews the literature and sets out the gap, objectives and plan. Chapter 3 covers requirements and feasibility, Chapter 4 the design, Chapter 5 the modules and testing, "
        "Chapter 6 the demonstration, Chapter 7 the results and cost, Chapter 8 the conclusion and Chapter 9 the references. Appendix A holds sample code.")


def ch2(D):
    D.chapter_start("Project Description and Goals")
    D.h2("Literature Review")
    D.p("We reviewed work in four groups: the flattening problem itself, the OCEL format, the consequences and data-quality issues of object-centric data, and the educational and capstone literature. "
        "Table 2.1 summarises the papers that matter most for our questions. The full reference list is in Chapter 9.")
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
    D.p("//The flattening problem.// van der Aalst [1] explained why one-case-per-event logs misrepresent processes with several interacting entities, and Adams and van der Aalst [4] "
        "went on to address convergence, divergence and deficiency. Both are conceptual. Neither says how often these effects occur on real data.")
    D.p("//The format.// OCEL 2.0 [2] is the interchange standard we build on. It stores events, objects, event-to-object (E2O) relations and object-to-object (O2O) relations, each with qualifiers, "
        "in JSON, XML or SQLite. We use the SQLite form for our own converters and read the JSON and XML forms of the public logs.")
    D.p("//Consequences and quality.// Waibel et al. [5] showed with a causal event graph that one-to-many links produce false directly-follows edges, but on a single company's data. "
        "Kabierski et al. [6] classified quality issues in object-centric data. They describe the kinds of problems; they do not count them. Adams et al. [3] showed that keeping the object graph helps predictive tasks.")
    D.p("//Education and capstones.// Miri et al. [7] is the closest neighbour to our work: object-centric mining on Moodle data. We are therefore clear that we are not the first to use OCEL in education. "
        "Premchaiswadi and Porouhan [11] mined an online peer-review process with a single case notion. Hassani et al. [10] describe how a department supervises a large number of final-year projects, without event data.")

    D.h2("Research Gap")
    D.p("Reading the table above as a whole, we see three gaps.")
    D.bullets([
        "**Flattening problems are named, not measured.** Convergence and divergence appear as toy or single-case examples. Most object-centric evidence we found uses simulated logs.",
        "**Education and capstone work stays on learning-platform data.** Object-centric educational mining uses Moodle activity. A transactional review lifecycle (submit, review, reject, resubmit, score) has no public object-centric dataset.",
        "**Capstone portal logs cannot be had.** Searches of Zenodo, 4TU and the web found no public capstone or thesis-management event log, so the capstone claim cannot be tested directly.",
    ])
    D.p("Our angle is to measure on real review-like and multi-entity logs, to give the capstone an OCEL 2.0 model, and to state the limits plainly.")

    D.h2("Objectives")
    D.p("The project has five objectives, in the order we worked on them.")
    D.bullets([
        "**O1.** Model the capstone lifecycle as OCEL 2.0 from the documented portal behaviour.",
        "**O2.** Build a reproducible pipeline: download, verify, convert, load and analyse.",
        "**O3.** Measure flattening distortion on seven real logs without hand-picked rules.",
        "**O4.** Compare standard outputs (activity rankings, directly-follows edges, variants, entity counts) between flat and object-centric views.",
        "**O5.** Verify every result with independent checks and keep the code re-runnable.",
    ])
    D.p("The work touches two of the United Nations Sustainable Development Goals: Goal 4, Quality Education, because it concerns how academic review processes are recorded and understood; "
        "and Goal 9, Industry, Innovation and Infrastructure, because it contributes open tooling for object-centric process data. "
        "On the Technology Readiness Level scale we place the pipeline at TRL 4 (validated in the laboratory, on seven public logs) and portal integration at TRL 2 to 3. These levels are our own estimate.")

    D.h2("Problem Statement")
    D.p("Given an object-centric event log with several object types, and a choice of one object type as the case notion, we want to answer two questions. "
        "First, how much does the flat log differ from the object-centric log: how many events are copied, how many are dropped, and how many are mixed up? "
        "Second, do those differences change the outputs an analyst actually reads, namely activity rankings, directly-follows edges, process variants and entity rankings? "
        "We must answer both on real data only, with checks that do not depend on our own code, and we must specify the capstone lifecycle in OCEL 2.0 even though no portal data is available.")

    D.h2("Project Plan")
    D.p("Figure 2.1 shows the calendar of the work. Review 2 presented a prototype that was evaluated on synthetic data. The team decided to rely on real data only, so that prototype and its results "
        "were removed from this work. The plan below reflects the work after that decision.")
    D.figure("fig_timeline.png", "Project calendar, August to December 2026 (grey bars are not part of the delivered work)", 5.9)
    D.table("Work packages and status",
            ["Work package", "Content", "Status"],
            [["WP1", "Literature review and scope", "Completed"],
             ["WP2", "Platform study and OCEL 2.0 schema of the capstone lifecycle", "Completed (design only)"],
             ["WP3", "Re-scope to real data only; locate and download public logs", "Completed"],
             ["WP4", "Convert CROP and OULAD to OCEL 2.0; profile all seven logs", "Completed"],
             ["WP5", "Distortion metrics and consequence analysis", "Completed"],
             ["WP6", "Independent verification, report and presentation", "Completed"],
             ["WP7", "Independent labelling of the findings; more logs; journal manuscript", "Planned. The manuscript is in preparation and has not been submitted"]],
            [0.9, 4.2, 2.6])


def ch3(D):
    D.chapter_start("Technical Specification")
    D.h2("Requirements")
    D.h3("Functional")
    D.p("Table 3.1 lists the functional requirements and the module that satisfies each one. The modules are described in Chapter 5.")
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
    D.p("The whole study is written in Python with open libraries and runs on one laptop. The largest log, Ethereum, has 3.2 million events and does not fit in 8 GiB of memory, "
        "so we analyse a contiguous window of 300,000 events and say so wherever the log is used. For the Enron log, the distortion analysis took about 9.5 seconds and the consequence analysis about 4 seconds. "
        "The technical risk was therefore correctness, not speed, and Chapter 5 spends its space on verification.")
    D.h3("Economic Feasibility")
    D.p("The project needed no purchase of data, software or cloud services. Table 3.3 lists the cost items. The only cost we cannot put a number on is our own time.")
    D.table("Cost items",
            ["Item", "Source", "Incremental cost"],
            [["Datasets (seven logs)", "Zenodo and UCI repositories, CC BY 4.0", "Nil"],
             ["Analysis software", "Python and open-source libraries (see Section 3.3.2)", "Nil"],
             ["Hardware", "A laptop the team already owned", "Nil"],
             ["Storage", "About 1.3 GB of downloaded and extracted files and 132 MB of derived OCEL files", "Nil"],
             ["Cloud or paid services", "None used", "Nil"]],
            [2.2, 3.4, 1.4])
    D.p("One licence caveat is worth stating. The `pm4py` library is released under the AGPL-3.0 licence. We use it as a reference implementation of flattening. "
        "If the code is released, the team must either choose a compatible licence or replace `pm4py` with a small SQLite loader.")
    D.h3("Social Feasibility")
    D.p("Two of the logs contain data about people: Enron holds real e-mail addresses, and CROP holds developer names that its authors already pseudonymised. "
        "We hash identifiers again when a log is loaded and never print raw values. We used no VIT student, guide or portal record. "
        "The benefit goes to anyone who analyses multi-entity workflows, academic review included, because they can see in advance what a flat view hides.")

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
    D.p("Figure 4.1 shows the pipeline from left to right. Seven public logs enter on the left. The acquisition stage downloads each file, checks it against the publisher's record where one exists, "
        "and writes down a SHA-256. A separate stage extracts archives safely. The conversion stage turns CROP and OULAD into OCEL 2.0 and loads every log into the same four tables: events, objects, "
        "event-to-object links and object-to-object links.")
    D.figure("fig_architecture.png", "System architecture of the flattening study", 6.3)
    D.p("Three analysis engines read the common tables. The distortion engine computes deficiency, convergence, divergence and coupling for every case notion. "
        "The consequence engine compares flat and object-centric outputs. The rule-based engine is the appendix-level component. "
        "The validation stage re-implements the key computations independently. Everything ends as CSV, JSON and Markdown files from which the report and the paper are written. "
        "The dashed box at the top is not built: it marks where an adapter from the portal's audit log would attach if de-identified logs are ever approved.")

    D.h2("Design")
    D.h3("Data Flow Diagram")
    D.p("The level-0 diagram in Figure 4.2 shows the system as one process with two external parties. Public data publishers supply dataset archives and licences. "
        "The researchers and the guide supply run commands and settings and receive tables, figures and validation status.")
    D.figure("fig_dfd0.png", "Data flow diagram, level 0", 5.6)
    D.p("Figure 4.3 opens the process into six. Process 1.0 acquires and verifies archives into store D1. Process 2.0 extracts and converts them into the OCEL logs of store D2. "
        "Processes 3.0 (distortion metrics) and 4.0 (consequence analysis) read D2 and write the metric tables of store D3. Process 5.0 validates, and process 6.0 summarises the results for the researchers.")
    D.figure("fig_dfd1.png", "Data flow diagram, level 1", 6.2)
    D.h3("Use Case Diagram")
    D.p("Figure 4.4 shows the two actors. The researcher (the team) can download and verify datasets, convert a source to OCEL 2.0, compute distortion metrics, run the consequence analysis, validate against independent code and export tables. "
        "The guide or panel reviews the results and approves them.")
    D.figure("fig_usecase.png", "Use case diagram", 5.6)
    D.h3("Class Diagram")
    D.p("Figure 4.5 shows the main data structures. `Ocel` holds the four tables of a loaded log. `Prepared` wraps an `Ocel` with integer-coded arrays so that rankings and directly-follows counts are fast. "
        "`View` and `Predicate` belong to the rule-based engine: a predicate is evaluated on a view of the log (native, flat or denormalised flat). "
        "In the code, the loader and the registry are modules of functions rather than classes; they are drawn as classes here so that their responsibilities are visible.")
    D.figure("fig_class.png", "Class diagram of the main structures", 6.0)
    D.h3("Sequence Diagram")
    D.p("Figure 4.6 follows one full run. The researcher starts the download, which verifies and records each file. Conversion writes OCEL 2.0 SQLite. "
        "The distortion engine asks the loader for an `Ocel` and writes its JSON results. The consequence engine does the same. "
        "The self-check re-computes the directly-follows pairs and the entity ranking with plain Python, and finally the summaries are written.")
    D.figure("fig_sequence.png", "Sequence diagram of one end-to-end run", 6.2)

    D.h2("OCEL 2.0 Model of the Capstone Lifecycle (Design Only)")
    D.p("This section describes the model we designed for the capstone portal. It is a design, not a result. We derived it from the portal's documentation (the audit-trail, submission-system and scoring-system documents in the repository) "
        "and have not populated it with portal data, because none is available.")
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
    D.p("The portal records an audit-log row for every state transition. The documented action vocabulary gives eight event types: `PROJECT_CREATED`, `COMPILATION_STARTED`, `COMPILATION_SUCCESS`, `COMPILATION_FAILED`, "
        "`STUDENT_SUBMITTED`, `FACULTY_STARTED_VERIFICATION`, `FACULTY_ACCEPTED` and `FACULTY_REJECTED`. Each row carries a project identifier, the acting student or faculty member, and a timestamp. "
        "In the model, an event is related to its project, to the acting student or faculty member, and, through joins on the project, to the team, the report version and the stage.", jc="left")
    D.p("The documentation also records facts that shape the model. A score is written once and then locked. A rejection uses one of three attempts and increments the report version. "
        "Compilation failures are free retries and do not use an attempt. The documentation lists the automatic advance from stage R1 to R2 to R3 as a known gap, so the stage relation is part of the design but is not fully populated by the current system.")
