import os
import re
import pandas as pd

SUITES = [
  "cpu2017", "dlrm", "gapbs", "gpt-2",
  "parsec", "pbbs", "phoronix", "redis", "xsbench",
]

BASE = os.path.dirname(os.path.abspath(__file__))
EVENTS_FILE = os.path.normpath(os.path.join(BASE, "..", "cpu2017", "perf_events.txt"))


def load_events():
  """Load perf-event names from cpu2017/perf_events.txt (one per line, blanks ignored).
  Prepends 'time' so the wall-clock from `seconds time elapsed` is captured."""
  events = ["time"]
  with open(EVENTS_FILE) as f:
    for line in f:
      name = line.strip()
      if not name or name.startswith("#"):
        continue
      events.append(name)
  return events


EVENTS = load_events()


def parse_run_id(stem):
  """Return (run_type, dram_weight, cxl_weight, dram_ratio, remote_ratio, label).
  remote_ratio is the CXL share (0.0 = all DRAM, 1.0 = all CXL)."""
  if stem == "L100-100":
    return "L100", None, None, 1.0, 0.0, "L100"
  if stem == "L0-1":
    return "L0", None, None, 0.0, 1.0, "L0"
  m = re.match(r"CXL-Interleave-(\d+)-(\d+)$", stem)
  if m:
    j, i = int(m.group(1)), int(m.group(2))
    dram_ratio = j / (j + i)
    return "Interleave", j, i, dram_ratio, 1.0 - dram_ratio, f"{j}:{i}"
  return (None,) * 6


def parse_data_file(path):
  """Parse a perf-stat .data file; returns dict event-name -> float (NaN if absent)."""
  result = {e: float("nan") for e in EVENTS}
  with open(path) as f:
    for line in f:
      tokens = [t for t in line.split() if t]
      if not tokens:
        continue
      if "<not" in tokens and "counted>" in tokens:
        continue
      for e in EVENTS:
        if e in tokens:
          try:
            result[e] = float(tokens[0].replace(",", ""))
          except ValueError:
            pass
  return result


def collect():
  rows = []
  for suite in SUITES:
    rst_dir = os.path.normpath(os.path.join(BASE, "..", suite, "rst"))
    if not os.path.isdir(rst_dir):
      continue
    for workload in sorted(os.listdir(rst_dir)):
      wl_dir = os.path.join(rst_dir, workload)
      if not os.path.isdir(wl_dir):
        continue
      for fname in sorted(os.listdir(wl_dir)):
        if not fname.endswith(".data"):
          continue
        stem = fname[:-5]
        run_type, dw, cw, dram_ratio, remote_ratio, label = parse_run_id(stem)
        if run_type is None:
          continue
        data = parse_data_file(os.path.join(wl_dir, fname))
        row = {
          "suite": suite,
          "workload": workload,
          "run_type": run_type,
          "dram_weight": dw,
          "cxl_weight": cw,
          "dram_ratio": dram_ratio,
          "remote_ratio": remote_ratio,
          "label": label,
        }
        row.update(data)
        rows.append(row)
  return pd.DataFrame(rows)


def main():
  out_dir = os.path.join(BASE, "csv")
  os.makedirs(out_dir, exist_ok=True)
  df = collect()
  if df.empty:
    print("No data found - make sure rst/ directories are populated.")
    return
  out = os.path.join(out_dir, "all_data.csv")
  df.to_csv(out, index=False)
  print(f"Wrote {len(df)} rows -> {out}")
  for suite, grp in df.groupby("suite"):
    wl_count = grp["workload"].nunique()
    run_count = len(grp)
    print(f"  {suite}: {wl_count} workload(s), {run_count} run(s)")


if __name__ == "__main__":
  main()
