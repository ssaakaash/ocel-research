.PHONY: check study

# Public-data observability study (needs realdata/.venv; see realdata/README.md for first-time setup)
study:
	cd realdata && .venv/bin/python -I src/run_cooc.py && .venv/bin/python -I src/analyze_cooc.py && python3 -I src/sql_crosscheck.py

check:
	python3 scripts/check_package.py
