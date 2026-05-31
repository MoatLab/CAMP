import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Force non-interactive backend
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, "csv", "all_data.csv")
PLOTS_DIR = os.path.join(BASE, "plots")

# Events the decomposition reads.
EVENTS_NEEDED = [
  "cycles",
  "EXE_ACTIVITY.BOUND_ON_STORES",
  "CYCLE_ACTIVITY.STALLS_MEM_ANY",
  "CYCLE_ACTIVITY.STALLS_L3_MISS",
]

COMPONENTS = [
  ("store", "lightcoral",     lambda d: d["EXE_ACTIVITY.BOUND_ON_STORES"]),
  ("DRAM",  "cornflowerblue", lambda d: d["CYCLE_ACTIVITY.STALLS_L3_MISS"]),
  ("cache", "forestgreen",    lambda d: d["CYCLE_ACTIVITY.STALLS_MEM_ANY"] - d["CYCLE_ACTIVITY.STALLS_L3_MISS"]),
]

BASELINE_RATIO = 0.0  # L100 — all-DRAM run


# ---------- data loading helpers ----------

def load_csv(path):
  if not os.path.isfile(path):
    raise FileNotFoundError(f"{path} not found. Run update_data.py first.")
  df = pd.read_csv(path)
  if df.empty:
    raise ValueError(f"{path} is empty")
  return df


def determine_ratios(group):
  """Sorted unique remote_ratio values present in `group` (one workload's rows)."""
  vals = group["remote_ratio"].dropna().tolist()
  return sorted({round(float(r), 2) for r in vals})


def get_array(group, event, ratios):
  """Return np.array of `event` values in `group`, indexed by `ratios` order."""
  by_ratio = {round(float(r["remote_ratio"]), 2): r[event] for _, r in group.iterrows()}
  return np.asarray([by_ratio.get(rt, np.nan) for rt in ratios], dtype=float)


def get_labels(group, ratios):
  """Return list of human labels (e.g. 'L100', '4:1', 'L0') in `ratios` order."""
  by_ratio = {round(float(r["remote_ratio"]), 2): r["label"] for _, r in group.iterrows()}
  return [by_ratio.get(rt, "?") for rt in ratios]


# ---------- decomposition ----------

def compute_breakdown(arrays, baseline_idx):
  """Decompose Δcycles vs baseline into the COMPONENTS plus 'other' and 'total'.
  Each output value is a fraction of cycles_baseline."""
  c0 = arrays["cycles"][baseline_idx]
  deltas = {e: arrays[e] - arrays[e][baseline_idx] for e in EVENTS_NEEDED}
  total = deltas["cycles"] / c0
  parts = {name: fn(deltas) / c0 for name, _, fn in COMPONENTS}
  parts["other"] = total - sum(parts.values())
  parts["total"] = total
  return parts


# ---------- plotting ----------

def plot_breakdown(suite, workload, ratios, labels, parts, out_path):
  x_pct = np.asarray(ratios, dtype=float) * 100.0

  # Cumulative boundary lines: y0=0, y1=store, y2=store+DRAM, y3=+cache, y4=+other.
  # The gap between two adjacent boundary lines equals that component's slowdown.
  band_names = [name for name, _, _ in COMPONENTS] + ["other"]
  band_colors = [color for _, color, _ in COMPONENTS] + ["gold"]
  band_values = [np.maximum(0.0, parts[name]) for name in band_names]
  boundaries = [np.zeros_like(x_pct)]
  for vals in band_values:
    boundaries.append(boundaries[-1] + vals)

  fig, ax = plt.subplots(figsize=(7, 4.5))
  for name, color, lower, upper in zip(band_names, band_colors, boundaries[:-1], boundaries[1:]):
    ax.fill_between(x_pct, lower, upper, color=color, label=name, alpha=0.85)
  # Explicit black boundary lines with marker dots at every measurement.
  for y in boundaries[1:]:
    ax.plot(x_pct, y, color="black", linewidth=0.7, marker="o", markersize=4)
  # Measured total as a dashed line+markers so any noise-floor clipping is visible.
  ax.plot(x_pct, parts["total"], color="black", linewidth=1.0, linestyle="--",
          marker="o", markersize=5, markerfacecolor="white", zorder=6,
          label="measured total")

  ax.set_xlim(0, 100)
  ax.set_xticks(np.arange(0, 101, 10))
  #ax.set_ylim(bottom=0)
  ax.set_xlabel("Remote share (%)", fontsize=10)
  ax.set_ylabel("Slowdown vs L100 (fraction of baseline cycles)", fontsize=10)
  ax.set_title(f"{suite} / {workload}", fontsize=11)
  ax.axhline(0, color="black", linewidth=0.5)
  ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), borderpad=0.3,
            labelspacing=0.3, prop={"size": 8})
  ax.grid(axis="both", linestyle=":", linewidth=0.5, alpha=0.6)
  plt.tight_layout()

  os.makedirs(os.path.dirname(out_path), exist_ok=True)
  plt.savefig(out_path, dpi=130)
  plt.close(fig)


# ---------- orchestration ----------

def process_workload(suite, workload, group):
  ratios = determine_ratios(group)
  if BASELINE_RATIO not in ratios:
    print(f"  skip {suite}/{workload}: no L100 baseline in CSV")
    return False
  baseline_idx = ratios.index(BASELINE_RATIO)

  arrays = {e: get_array(group, e, ratios) for e in EVENTS_NEEDED}
  if np.isnan(arrays["cycles"][baseline_idx]):
    print(f"  skip {suite}/{workload}: baseline cycles is NaN")
    return False

  labels = get_labels(group, ratios)
  parts = compute_breakdown(arrays, baseline_idx)

  out = os.path.join(PLOTS_DIR, f"{suite}__{workload}.png")
  plot_breakdown(suite, workload, ratios, labels, parts, out)
  print(f"  wrote {out}")
  return True


def main():
  try:
    df = load_csv(CSV_PATH)
  except (FileNotFoundError, ValueError) as e:
    print(f"error: {e}")
    return

  all_ratios = sorted({round(float(r), 2) for r in df["remote_ratio"].dropna()})
  print(f"Found ratios in CSV: {all_ratios}")

  n_done = 0
  for (suite, workload), group in df.groupby(["suite", "workload"]):
    if process_workload(suite, workload, group):
      n_done += 1
  print(f"Done. {n_done} plot(s) written to {PLOTS_DIR}/")


if __name__ == "__main__":
  main()
