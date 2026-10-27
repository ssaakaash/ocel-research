# realdata — public-data observability study

Executable COOC (Cross-Object Observability Coverage) experiments on public OCEL / event data. Nothing here is Educational Capstone Portal data; see `docs/research/Journal_Paper_Research_Plan.md` for the plan and `docs/research/Journal_Manuscript_Draft.md` for the draft paper.

## Layout

| Path | Purpose |
|---|---|
| `sources.json` | Dataset manifest (Zenodo record, files, DOI, licence). |
| `src/fetch_sources.py` | Downloads to `raw/<id>/`, verifies Zenodo MD5 and size, writes `SOURCE.md` with SHA-256. |
| `src/ocel_io.py` | Loads OCEL (SQLite/XML/JSON) into pandas; flattening statistics (deficiency, convergence, divergence). |
| `src/convert_crop.py`, `src/convert_oulad.py` | Build OCEL 2.0 SQLite from CROP (Gerrit) and OULAD. |
| `src/cooc.py` | Views (native, flat, denormalised flat, leading), predicate templates, expressibility and correctness. |
| `src/registry.py` | The predicate registry (what is measured, and why). |
| `src/inject.py` | Minimal violation injection when natural positives < 5. |
| `src/run_cooc.py`, `src/analyze_cooc.py`, `src/run_seeds.sh` | Experiment runner, aggregation with bootstrap CIs, multi-seed run. |
| `src/sql_crosscheck.py` | Independent stdlib-SQLite check of four CROP predicates. |
| `raw/`, `ocel/` | Downloaded and derived data. **Git-ignored; not redistributed.** |
| `results/` | CSV/JSON outputs; `results/profiles/*.json` dataset profiles. |

## Reproduce

```bash
cd realdata
uv venv .venv --python 3.14 && VIRTUAL_ENV=.venv uv pip install --python .venv/bin/python -r requirements.txt
python3 -I src/fetch_sources.py                     # ~350 MB, checksum-verified
python3 -I - <<'PY'                                  # extract archives into new directories
import zipfile, os
os.makedirs("raw/T3a_crop_x"); zipfile.ZipFile("raw/T3a_crop/metadata.zip").extractall("raw/T3a_crop_x")
os.makedirs("raw/T2a_oulad_x"); z = zipfile.ZipFile("raw/T2a_oulad/oulad_uci_349.zip")
[z.extract(n, "raw/T2a_oulad_x") for n in z.namelist() if n != "studentVle.csv"]
PY
.venv/bin/python -I src/convert_crop.py && .venv/bin/python -I src/convert_oulad.py
.venv/bin/python -I src/profile_all.py
.venv/bin/python -I src/run_cooc.py && .venv/bin/python -I src/analyze_cooc.py
python3 -I src/sql_crosscheck.py
```

## Caveats you must keep when quoting results

- Native COOC is 100 % by definition. The oracle code is validated only by the SQL cross-check and an independent OULAD recomputation.
- 21 of 41 evaluated predicates use injected violations; 6 of 8 datasets are simulated.
- Predicates were written after reading each dataset's vocabulary. Two degenerate rules were removed and the LOAD threshold rule was changed after the first run (see `registry.py` header).
- `pm4py` is AGPL-3.0. Decide the licence for released code or replace it with a small sqlite3 loader.
- Registry SHA-256 at the time of this write-up: `d54d14a08f6f2093508ce5ec9428a2cf63e8f84d7c4965309c2348b6f31fd3d5`.
- Person names in CROP are already pseudonymised by its authors and are hashed again here. Do not publish raw CROP text.
