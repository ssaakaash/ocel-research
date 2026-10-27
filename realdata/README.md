# realdata — public-data observability study

Executable COOC (Cross-Object Observability Coverage) experiments on public OCEL / event data. Nothing here is Educational Capstone Portal data; see `docs/research/Journal_Paper_Research_Plan.md` for the plan and `docs/research/Journal_Manuscript_Draft.md` for the draft paper.

## Layout

| Path | Purpose |
|---|---|
| `sources.json` | Dataset manifest (Zenodo record, files, DOI, licence). |
| `src/fetch_sources.py` | Downloads to `raw/<id>/`, verifies Zenodo MD5 and size, writes `SOURCE.md` with SHA-256. |
| `src/ocel_io.py` | Loads OCEL (SQLite/XML/JSON) into pandas; flattening statistics (deficiency, convergence, divergence). |
| `src/extract_archives.py` | Safe extraction of downloaded zips into new directories (rejects unsafe member paths). |
| `src/convert_crop.py`, `src/convert_oulad.py` | Build OCEL 2.0 SQLite from CROP (Gerrit) and OULAD. |
| `src/cooc.py` | Views (native, flat, denormalised flat, leading), predicate templates, expressibility and correctness. |
| `src/registry.py` | The predicate registry (what is measured, and why). |
| `src/distortion.py` | Predicate-free flattening-distortion and cross-case coupling metrics (the current main analysis). |
| `src/run_cooc.py`, `src/analyze_cooc.py` | Predicate-based COOC runner and aggregation (appendix-level; natural prevalence only). |
| `src/consequence.py`, `src/summarize_consequence.py` | Consequence analysis: activity rankings, directly-follows frequencies, spurious edges, variants, entity rankings (flat vs object-centric). |
| `src/check_consequence.py` | Self-check of `consequence.py` against a plain-Python implementation on a real Enron slice. |
| `src/summarize_distortion.py` | Combines per-log distortion JSON into `distortion_summary.{csv,md}`. |
| `src/sql_crosscheck.py` | Independent stdlib-SQLite check of four CROP predicates. |
| `raw/`, `ocel/` | Downloaded and derived data. **Git-ignored; not redistributed.** |
| `results/` | CSV/JSON outputs; `results/profiles/*.json` dataset profiles. |

## Reproduce

```bash
cd realdata
uv venv .venv --python 3.14 && VIRTUAL_ENV=.venv uv pip install --python .venv/bin/python -r requirements.txt
python3 -I src/fetch_sources.py                     # ~350 MB, checksum-verified
python3 -I src/extract_archives.py                # safe extraction into new directories
.venv/bin/python -I src/convert_crop.py && .venv/bin/python -I src/convert_oulad.py
.venv/bin/python -I src/profile_all.py
.venv/bin/python -I src/run_cooc.py && .venv/bin/python -I src/analyze_cooc.py
.venv/bin/python -I src/distortion.py && python3 -I src/summarize_distortion.py
.venv/bin/python -I src/check_consequence.py && .venv/bin/python -I src/consequence.py && python3 -I src/summarize_consequence.py
python3 -I src/sql_crosscheck.py
```

## Caveats you must keep when quoting results

- Native COOC is 100 % by definition. The oracle code is validated only by the SQL cross-check and an independent OULAD recomputation.
- Real data only: no simulated logs and no injected violations. COOC currently has 11 predicates over 2 logs, too few for inference.
- Predicates were written after reading each dataset's vocabulary, so the predicate set is not blind. The capacity threshold is data-adaptive (floor of the median peak load; see `registry.py` header).
- `pm4py` is AGPL-3.0. Decide the licence for released code or replace it with a small sqlite3 loader.
- Registry SHA-256 at the time of this write-up: `10b60b9439d5db3d5da62601c2a5b0466096b1381264b0d1b7a620d7d92470a5`.
- Person names in CROP are already pseudonymised by its authors and are hashed again here. Do not publish raw CROP text.
