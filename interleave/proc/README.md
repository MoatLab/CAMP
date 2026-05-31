# Interleave slowdown breakdown

Tools to turn raw `perf stat` runs of workloads under different DRAM:CXL
interleaving ratios into per-workload **slowdown breakdown plots** (where the
slowdown comes from) and **predicted vs measured slowdown plots** with a
best-ratio report (which ratio minimizes each kind of slowdown).

## Data layout

Raw perf output lives one level above this directory, organized by suite (example):

```
interleave/
  <suite>/rst/<workload>/L100-100.data            # all DRAM,   0% remote
  <suite>/rst/<workload>/CXL-Interleave-4-1.data  # 4:1 ratio, 20% remote
  <suite>/rst/<workload>/CXL-Interleave-3-2.data  # 3:2 ratio, 40% remote
  <suite>/rst/<workload>/CXL-Interleave-2-3.data  # 2:3 ratio, 60% remote
  <suite>/rst/<workload>/CXL-Interleave-1-4.data  # 1:4 ratio, 80% remote
  <suite>/rst/<workload>/L0-1.data                # all CXL, 100% remote
```

The interleave weights `j:i` in `CXL-Interleave-j-i.data` are interpreted as
DRAM:CXL, so `remote_ratio = i / (j + i)`.

Suites scanned: `cpu2017`, `dlrm`, `gapbs`, `gpt-2`, `parsec`, `pbbs`,
`phoronix`, `redis`, `xsbench`. Missing `rst/` directories are silently
skipped.

## Scripts

| Script            | Role                                                                            |
|-------------------|---------------------------------------------------------------------------------|
| `update_data.py`  | Ingest raw `.data` files into a single tidy CSV.                                |
| `prof.py`         | **Measured** slowdown decomposition (stacked-area plot per workload).           |
| `pred.py`         | **Predicted** slowdown (cubic fit) + best-ratio report; importable helpers.     |

## Workflow

```bash
bash setup.sh                 # one-time: install uv, create .venv, deps
source .venv/bin/activate

python update_data.py         # raw .data files -> csv/all_data.csv
python prof.py                # csv/all_data.csv -> plots/<suite>__<workload>.png
python pred.py                # cubic fit -> _pred plots + csv/min_slowdown.csv

# optional: use externally-predicted endpoint stall cycles instead of L0 row
python pred.py --c2-csv csv/c2_example.csv
```

`prof.py` and `pred.py` both read `csv/all_data.csv` and are independent — run
either or both after `update_data.py`.

## Outputs

- `csv/all_data.csv` — one row per `.data` file, columns:
  `suite, workload, run_type, dram_weight, cxl_weight, dram_ratio,
  remote_ratio, label, time, cycles, <perf events...>`
- `plots/<suite>__<workload>.png` — **measured** decomposition (from
  `prof.py`). Stacked-area chart with explicit black boundary lines and marker
  dots at every measurement. X-axis is the continuous remote share in % (0 →
  100, ticks every 10%); Y-axis is slowdown vs L100 as a fraction of baseline
  cycles. The **gap between two adjacent boundary lines is that component's
  slowdown contribution** at that remote share. A dashed black "measured
  total" line with hollow markers overlays the top of the stack so any
  clipping is visible.
- `plots/<suite>__<workload>__sd_{dram,cache,store}_pred.png`,
  `plots/<suite>__<workload>__sd_pred.png` — **measured vs predicted** for
  each of the four components (from `pred.py`). Black markers = measured;
  red line = closed-form cubic prediction.
- `csv/min_slowdown.csv` — per `(suite, workload, component)` row with the
  three "best ratio" answers (from `pred.py`):
  `pred_cont_y / pred_cont_ratio_pct`,
  `pred_meas_y / pred_meas_ratio_pct`,
  `meas_y      / meas_ratio_pct`.

## Slowdown decomposition (`prof.py`)

Let `c0 = cycles_L100` and `ΔE = E - E_L100` for any event `E`. Then for each non-baseline run, L1/L2/L3 stalls are bundled into a single `cache` component:


| Component | Formula                                                                |
|-----------|------------------------------------------------------------------------|
| `total`   | `Δcycles / c0`                                                         |
| `store`   | `ΔEXE_ACTIVITY.BOUND_ON_STORES / c0`                                   |
| `DRAM`    | `ΔCYCLE_ACTIVITY.STALLS_L3_MISS / c0`                                  |
| `cache`   | `(ΔCYCLE_ACTIVITY.STALLS_MEM_ANY − ΔCYCLE_ACTIVITY.STALLS_L3_MISS) / c0` |
| `other`   | `total − (store + DRAM + cache)`                                       |

Negative components (counter noise) are clipped to zero in the stack; the
black `total` tick still reflects the unclipped sum, so any clipping is
visible.

## Prediction model (`pred.py`)

For each component (`dram`, `cache`, `store`) the predicted slowdown at remote
share `x ∈ [0, 1]` is a cubic-asymmetric mix of the baseline (L100) and
endpoint (L0) stall counts, weighted by per-component memory latencies:

```
A = C1*(r1-1)/r1,  B = C1/r1,  P = C2*(r2-1)/r2,  Q = C2/r2
y(x) = ((A*(1-x)^3 + B*(1-x)) + (P*x^3 + Q*x) - C1) / cyc1
     = d1*x + d2*x^2 + d3*x^3
```

- `C1`, `C2` — stall cycles at L100 and L0 for the component.
- `L1`, `L2` — per-component memory latency at L100 and L0 (see table below).
- `cyc1` — `cycles_L100`.

The `total` prediction is the sum of the three component predictions.

| Component | Stall counter `C`                                          | Latency `L` (offcore-based)                                                                                                       |
|-----------|------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `dram`    | `CYCLE_ACTIVITY.STALLS_L3_MISS`                            | `OFFCORE_REQUESTS_OUTSTANDING.ALL_DATA_RD / OFFCORE_REQUESTS.ALL_DATA_RD`                                                         |
| `cache`   | `CYCLE_ACTIVITY.STALLS_MEM_ANY - CYCLE_ACTIVITY.STALLS_L3_MISS` | `(ALL_DATA_RD_outstanding − DEMAND_DATA_RD_outstanding) / (ALL_DATA_RD − DEMAND_DATA_RD)`                                         |
| `store`   | `EXE_ACTIVITY.BOUND_ON_STORES`                             | `OFFCORE_REQUESTS_OUTSTANDING.DEMAND_RFO / OFFCORE_REQUESTS.DEMAND_RFO`                                                           |

### External-C2 mode (`--c2-csv`)

`Bandwidth-bound workloads`: By default `C2` (the endpoint stall cycles per component) is read from the L0
row of `csv/all_data.csv`.

`Latency-bound workloads`: With `--c2-csv PATH`, `pred.py` instead reads `C2`
from a consolidated CSV — one row per workload. It gives the
slowdown curve when the endpoint can be *predicted* (i.e. the CXL/NUMA prediction model).

Example:
```csv
workload,dram_c2,cache_c2,store_c2
503.bwaves_r,16477008623.0,50387326727.0,5726357519.0
```

Behavior changes:

- `r2 = L2 / L20` is forced to **1** (so `L2` is not consulted and the `t2`
  term reduces to `C2 * x`).
- Only workloads listed in the CSV are processed; others are logged as
  `skip: no external C2`.
- The L0 (`remote_ratio = 1.0`) row is **not** required — only the L100
  baseline is.

### Best-ratio report

For each component `pred.py` reports three "min y / ratio" pairs:

- **`pred_cont`** — closed-form minimum on `[0, 1]`.
- **`pred_meas`** — minimum of the *predictor* evaluated only at the measured
  ratios.
- **`meas`**     — minimum of the *measured* slowdown across the measured
  ratios (one of the runs in `csv/all_data.csv`).

`ratio%` is the remote share (CXL fraction) in percent.

