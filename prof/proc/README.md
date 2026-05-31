# proc

Post-processing scripts for perf stat results.

## Prerequisites

- Python 3
- Raw perf stat data in `rst/` (one subdirectory per workload, each containing `L100-100.data` for LOCAL and `L0-1.data` for NUMA)

## Setup

Install dependencies (only needed once):

```bash
bash setup.sh
source .venv/bin/activate
```

## Running

- **Workload analysis** (the common case) uses only `prof.py`. It consumes a `params.txt` produced from microbenchmark calibration.
- **Microbenchmark calibration** (run once, or whenever the model needs to be re-fit) uses `param.py` to produce `params.txt`.

### Workload analysis — what to run for workloads

This is the only path you need for analyzing workloads. It assumes `params.txt` already exists in this directory (from a prior microbenchmark calibration — see below).

**Step 1 — parse raw workload data into CSV:**

```bash
python update_data.py
```

Reads `rst/` (populated with workload perf-stat data), writes per-memory-type CSVs and a merged CSV to `csv/`.

**Step 2 — analyze workloads:**

```bash
python prof.py
```

Reads `csv/`, computes per-workload slowdown decomposition (store / DRAM / L3 / L2 / L1 / other) and writes `plots/sd_breakdown.png`. It also loads the fitted equations from `params.txt`, computes a predicted slowdown per workload for each model, prints the actual-vs-predicted pearson correlation, and writes one CSV per slowdown type (formula inputs, actual slowdown, predicted slowdown) into `csv-metrics/`.

### Microbenchmark calibration — how `params.txt` is produced

The slowdown model coefficients in `params.txt` come from running `param.py` against **microbenchmark** data (not workload data). This is done separately and the resulting `params.txt` is then reused by `prof.py` for any number of workload runs.

```bash
python update_data.py   # rst/ contains microbenchmark perf-stat data
python param.py
```

`param.py` fits the cache, demand-read, and store slowdown models against the microbenchmark measurements and writes the fitted equations (with coefficients A, B, C, D) to `params.txt`.

## Output

| Path | Contents |
|---|---|
| `csv/mLOCAL.csv` | LOCAL memory counters per workload |
| `csv/mNUMA.csv` | NUMA memory counters per workload |
| `csv/merged.csv` | Combined table used by `prof.py` |
| `params.txt` | Fitted slowdown equations from `param.py` |
| `plots/sd_breakdown.png` | Stacked bar chart of slowdown breakdown |
| `csv-metrics/cache_slowdown.csv` | Per-workload cache slowdown: inputs, actual, predicted |
| `csv-metrics/demand_rd_slowdown.csv` | Per-workload demand-read slowdown: inputs, actual, predicted |
| `csv-metrics/store_slowdown.csv` | Per-workload store slowdown: inputs, actual, predicted |
