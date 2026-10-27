.PHONY: check study extended

# Public-data observability study (needs realdata/.venv; see realdata/README.md for first-time setup)
study:
	cd realdata && .venv/bin/python -I src/run_cooc.py && .venv/bin/python -I src/analyze_cooc.py && python3 -I src/sql_crosscheck.py \
		&& .venv/bin/python -I src/distortion.py && python3 -I src/summarize_distortion.py && python3 -I src/summarize_log_level.py && .venv/bin/python -I src/check_distortion.py --full \
		&& .venv/bin/python -I src/check_consequence.py && .venv/bin/python -I src/consequence.py && python3 -I src/summarize_consequence.py

# Robustness analyses for the journal version (bootstrap intervals, process discovery; roughly an hour on a laptop)
extended:
	cd realdata && .venv/bin/python -I src/bootstrap.py && .venv/bin/python -I src/discovery.py && python3 -I src/summarize_discovery.py

check:
	python3 scripts/check_package.py
