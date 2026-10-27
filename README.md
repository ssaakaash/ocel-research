# Object-Centric Event Log Mining for Academic Capstone Processes

> **Research status (2026-10-27):** the project has moved from the Review 2 synthetic proof of mechanism to a **public-data study**. The synthetic benchmark and the interactive demo were removed from the working tree; they remain in Git history (commit `28b629c`). The Review 2 slides and draft report in `docs/review-2/` still describe the synthetic results and have not been edited. This repository contains no production Educational Capstone Portal logs, real capstone PDFs, or measured institutional outcomes.

This Team 1 project investigates whether a native [OCEL 2.0](https://www.ocel-standard.org/2.0/) representation preserves the interacting entities of a review workflow (work item, actors, stages, versions, scores, shared resources), and which process-rule questions stop being answerable when the same data are flattened to one case notion.

## Research question

Conventional process mining selects one case identifier. A capstone event may simultaneously concern a project, three students, a guide, a review stage, a versioned report, and an immutable score. The central question is:

**Which process rules and risk predicates become unobservable, or wrongly answered, when this multi-entity lifecycle is flattened to one case notion, and what must a flat export carry to keep them answerable?**

The project does **not** claim to be the first use of object-centric process mining in education (Miri et al., 2026).

## Current approach

1. **COOC (Cross-Object Observability Coverage):** the share of a registered set of rule predicates that a representation can express *and* answer identically to an object-centric oracle. It is a study-specific diagnostic, not a universal quality standard.
2. **Three representation tiers:** native OCEL (oracle), plain case-centric flat log, and a denormalised flat log that keeps related object identifiers as columns.
3. **Real public datasets only (no synthetic or simulated data):** a Gerrit code-review corpus (CROP), a real education log (OULAD), and further real many-to-many logs under evaluation (see the re-scope note). All are openly licensed and downloaded locally, never redistributed here.
4. **Executable predicate registry** with an independent SQL cross-check of the oracle.

The novelty assessment and re-scope are in [`docs/research/Novelty_Assessment_and_Rescope.md`](docs/research/Novelty_Assessment_and_Rescope.md) (the earlier manuscript draft is superseded); the plan and its execution log are in [`docs/research/Journal_Paper_Research_Plan.md`](docs/research/Journal_Paper_Research_Plan.md).

## Repository layout

```text
.
├── docs/
│   ├── research/           Plan, manuscript draft, literature review, agenda, execution prompt
│   ├── review-1/           Team 1 Review 1 presentation
│   ├── review-2/           Review 2 presentation, draft report, and explanation guide (synthetic-era)
│   └── educational-capstone-platform/  Documentation used to derive the process model
├── realdata/               Public-data study: manifest, loaders, COOC engine, registry, results
├── scripts/                Repository-level validation
└── .github/workflows/      Package check
```

## Reproduce the public-data study

See [`realdata/README.md`](realdata/README.md) for first-time setup (virtual environment, checksum-verified downloads, conversions). Afterwards:

```bash
make study     # run the experiments, aggregate results, SQL cross-check
make check     # repository boundary check
```

## Team

| Member | Registration number |
|---|---|
| Aakaash Sathya Saravanan | 23BCE0500 |
| Mitisha Sharma | 23BCE0434 |
| Tanmay Khambete | 23BCE0498 |

Project guide: **Dr. Kalyanaraman P.**

## Key references

- [OCEL 2.0 specification](https://www.ocel-standard.org/2.0/ocel20_specification.pdf)
- [van der Aalst, Object-Centric Process Mining (2019)](https://doi.org/10.1007/978-3-030-30446-1_1)
- [Park and van der Aalst, Proc. ICPM (2021)](https://doi.org/10.1109/ICPM53251.2021.9576846)
- [Miri et al., multi-entity educational process mining (2026)](https://doi.org/10.1016/j.dajour.2026.100724)

## Responsible use

Do not add real student, faculty, score, submission, or capstone-document data to this repository, and do not commit third-party raw data. See [SECURITY.md](SECURITY.md) before connecting the pipeline to institutional data.
