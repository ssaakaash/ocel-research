#!/bin/bash
# Re-run injection-dependent datasets under several seeds and aggregate each seed.
cd "$(dirname "$0")/.."
for s in 101 102 103 104 105 106 107 108 109 110; do
  .venv/bin/python -I src/run_cooc.py p2p_berti hiring o2c hospital order_management container_logistics --seed $s > results/seedrun_$s.log 2>&1
  .venv/bin/python -I src/analyze_cooc.py --seed $s > results/seedanalyze_$s.log 2>&1
done
echo done > results/seeds_done.flag
