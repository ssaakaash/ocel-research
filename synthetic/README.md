# Synthetic OCEL benchmark

This folder contains a deterministic, dependency-free proof-of-mechanism benchmark.

## Generate

```bash
python3 src/team1_synthetic_ocel.py
```

The generator creates three scenario folders under `data/`, each containing objects, events, event-to-object links, object-to-object links, labelled anomaly ground truth, and an OCEL 2.0 SQLite export.

## Analyse

```bash
python3 src/analyze_team1_synthetic.py
```

The analysis produces integrity summaries, flattening ablations, anomaly-detection scores, transition-prediction results, observability coverage, and offline intervention simulations under `results/`.

All identities, timestamps, scores, durations, capacities, anomaly frequencies, and simulated outcomes are artificial.

