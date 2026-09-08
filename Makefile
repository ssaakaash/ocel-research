.PHONY: research check demo-install demo-build

research:
	python3 synthetic/src/team1_synthetic_ocel.py
	python3 synthetic/src/analyze_team1_synthetic.py

check:
	python3 scripts/check_package.py

demo-install:
	cd demo && pnpm install --frozen-lockfile

demo-build:
	cd demo && pnpm run build

