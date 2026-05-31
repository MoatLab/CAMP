import sys
import csv
import re
import matplotlib.pyplot as plt
import numpy as np
import os
import pylab
import pandas as pd

from scipy.stats import pearsonr
from scipy.stats import spearmanr
from scipy.optimize import curve_fit

events = ["time", "instructions", "cycles", "CYCLE_ACTIVITY.STALLS_MEM_ANY", \
  "EXE_ACTIVITY.BOUND_ON_STORES", "CYCLE_ACTIVITY.STALLS_L3_MISS", \
  "CYCLE_ACTIVITY.STALLS_L2_MISS", "CYCLE_ACTIVITY.STALLS_L1D_MISS", \
  "MEM_LOAD_RETIRED.L1_MISS", "MEM_LOAD_RETIRED.FB_HIT", \
  "OFFCORE_RESPONSE.PF_L1D_AND_SW.ANY_RESPONSE", \
  "OFFCORE_RESPONSE.PF_L1D_AND_SW.L3_HIT.ANY_SNOOP", \
  "OFFCORE_REQUESTS.DEMAND_DATA_RD", \
  "OFFCORE_REQUESTS_OUTSTANDING.CYCLES_WITH_DEMAND_DATA_RD", \
  "OFFCORE_REQUESTS_OUTSTANDING.DEMAND_DATA_RD"]

sd_m = ["cycles"]
load_sd_m = ["CYCLE_ACTIVITY.STALLS_MEM_ANY", "cycles"]
store_sd_m = ["EXE_ACTIVITY.BOUND_ON_STORES", "cycles"]
cache_sd_m = ["CYCLE_ACTIVITY.STALLS_MEM_ANY", "CYCLE_ACTIVITY.STALLS_L3_MISS", "cycles"]
dram_sd_m = ["CYCLE_ACTIVITY.STALLS_L3_MISS", "cycles"]
l1_sd_m = ["CYCLE_ACTIVITY.STALLS_MEM_ANY", "CYCLE_ACTIVITY.STALLS_L1D_MISS", "cycles"]
l2_sd_m = ["CYCLE_ACTIVITY.STALLS_L1D_MISS", "CYCLE_ACTIVITY.STALLS_L2_MISS", "cycles"]
l3_sd_m = ["CYCLE_ACTIVITY.STALLS_L2_MISS", "CYCLE_ACTIVITY.STALLS_L3_MISS", "cycles"]

def Linear(x, A, B):
  y = A * x + B
  return y

def Func1(x, B, C):
  y = 1/(B/x + C)
  return y

def check_file_exist(file):
  if not os.path.isfile(file):
    print(file + "is not existed")
    exit(0)

def get_vals(event_name, mem_type, csv_path):
  filename = os.path.join(csv_path, 'm'+str(mem_type)+'.csv')
  check_file_exist(filename)
  df = pd.read_csv(filename, index_col ="workload_id")
  columns = df.columns.values.tolist()
  assert event_name in events
  assert event_name in columns
  res = []
  for val in df[event_name]:
    res.append(val)
  return np.asarray(res)

def get_workloads(df):
  columns = df.columns.values.tolist()
  assert "workload_name" in columns
  workloads = []
  for name in df["workload_name"]:
    if name not in workloads:
      workloads.append(name)
  return workloads

def get_slowdowns(t1, t2, metric, csv_path):
  if len(metric) == 1:
    v1, v2 = get_vals(metric[0], t1, csv_path), get_vals(metric[0], t2, csv_path)
    return (v2-v1)/v1
  elif len(metric) == 2:
    v1, v2 = get_vals(metric[0], t1, csv_path), get_vals(metric[0], t2, csv_path)
    cyc1 = get_vals(metric[1], t1, csv_path)
    return (v2 - v1)/cyc1
  elif len(metric) == 3:
    a1, a2 = get_vals(metric[0], t1, csv_path), get_vals(metric[0], t2, csv_path)
    b1, b2 = get_vals(metric[1], t1, csv_path), get_vals(metric[1], t2, csv_path)
    cyc1 = get_vals(metric[2], t1, csv_path)
    return ((a2-b2)-(a1-b1))/cyc1
  elif len(metric) == 4:
    a1, a2 = get_vals(metric[0], t1, csv_path), get_vals(metric[0], t2, csv_path)
    b1, b2 = get_vals(metric[1], t1, csv_path), get_vals(metric[1], t2, csv_path)
    c1, c2 = get_vals(metric[2], t1, csv_path), get_vals(metric[2], t2, csv_path)
    cyc1 = get_vals(metric[3], t1, csv_path)
    return ((a2-a1)+(b2-b1)+(c2-c1))/cyc1
  print("error")
  exit(0)

def cal_vals(metric, latency, csv_path):
  vals = []
  events = metric['events']
  for e in events:
    vals.append(get_vals(e, latency, csv_path))
  return metric['function'](vals)

def draw_scatter(files, x, y, output_path, plot_name, xlabel, ylabel, title, func):
  # print(x, y)
  fig, ax = plt.subplots()
  # print(x, y)
  ax.scatter((x), (y))
  corr, _ = pearsonr((x), (y))

  files = [x[:] for x in files]
  for i, txt in enumerate(files):
    ax.annotate(txt, (x[i], y[i]), fontsize=7)

  xdata = np.asarray((x))
  ydata = np.asarray((y))
  parameters, covariance = curve_fit(func, xdata, ydata)
  plt.plot(xdata, func(xdata, parameters[0], parameters[1]))
  print(parameters, corr)

  ax.set_xlabel(xlabel)
  ax.set_ylabel(ylabel)
  plt.title(title)

  plt.subplots_adjust(bottom=0.15)
  plt.figtext(0.5, 0.01, "pearson correlation: "+str(round(corr, 2)), wrap=True, horizontalalignment='center', fontsize=10)
  plt.savefig(output_path + '/' + plot_name + '.png')
  plt.clf()

  return parameters

def draw_bars(x, ys, xlabel, ylabel, title, output_path, plot_name, labels, isylog, colors):
  color = iter(colors)
  if len(colors) < 1:
    color = iter(cm.rainbow(np.linspace(0, 1, len(ys))))
  else:
    assert len(colors) == len(ys)
  # print(y)
  xs = range(len(x))
  n = len(ys)
  maxval= 0.8
  index = [-(maxval)/2 + i * maxval/n for i in range(n)]
  # print(index)
  for idx, y in enumerate(ys):
    c = next(color)
    plt.bar([i+index[idx] for i in xs], height=y, width=maxval/n, label=labels[idx], color=c)
  # plt.legend()
  plt.xticks(xs, x, rotation='vertical', fontsize=6)
  plt.ylabel(ylabel, fontsize=9)
  plt.subplots_adjust(bottom=0.2)
  if isylog:
    plt.yscale("log")
  # plt.ylim([-10, 140])
  plt.title(title, fontsize=10)
  plt.legend(loc='upper center', borderpad=0.0, labelspacing=0.1, bbox_to_anchor=(1.02, 1.02))
  plt.savefig(output_path+'/'+plot_name+'.png')
  plt.clf()

def draw_bars_b(data, x, output_path, filename, loc, xlabel, ylabel, title):
  xs = range(len(x))
  [store_sd, dram_sd, l3_sd, l2_sd, l1_sd, other] = data

  plt.bar([i for i in xs], height=store_sd, width=0.3, \
    label='store', color='lightcoral')
  plt.bar([i for i in xs], height=dram_sd, width=0.3, \
    bottom=store_sd, label='DRAM', color='cornflowerblue')
  plt.bar([i for i in xs], height=l3_sd, width=0.3, \
    bottom=store_sd+dram_sd, label='l3', color='darkgreen')
  plt.bar([i for i in xs], height=l2_sd, width=0.3, \
    bottom=store_sd+dram_sd+l3_sd, label='l2', color='forestgreen')
  plt.bar([i for i in xs], height=l1_sd, width=0.3, \
    bottom=store_sd+dram_sd+l3_sd+l2_sd, label='l1', color='lime')
  plt.bar([i for i in xs], height=other, width=0.3, \
    bottom=store_sd+dram_sd+l3_sd+l2_sd+l1_sd, label='other', color='gold')
  plt.xticks(xs, x, rotation='vertical', fontsize=6)
  plt.xlabel(xlabel, fontsize=9)
  plt.ylabel(ylabel, fontsize=9)
  plt.subplots_adjust(bottom=0.25)
  plt.title(title, fontsize=10)
  plt.legend(loc='upper center', borderpad=0.0, labelspacing=0.1, \
    bbox_to_anchor=(loc[0], loc[1]), prop={'size': 7})
  plt.savefig(output_path+'/'+filename+'.png', format='png')
  plt.clf()

def main(configs):
  csv_path = "csv"
  isExist = os.path.exists(csv_path)
  if not isExist:
    print("error: csv is not exist")
    exit()

  params_file = "params.txt"
  if not os.path.isfile(params_file):
    print("error: params.txt is not exist, run param.py first")
    exit()
  with open(params_file) as f:
    param_lines = [ln.strip() for ln in f if ln.strip()]
  def _floats(line):
    return [float(x) for x in re.findall(r"-?\d+\.\d+", line)]
  A_c = B_c = None
  A_d = B_d = C_d = D_d = None
  A_s = B_s = None
  for ln in param_lines:
    if ln.startswith("Cache"):
      A_c, B_c = _floats(ln)
    elif ln.startswith("Demand Read"):
      A_d, B_d, C_d, D_d = _floats(ln)
    elif ln.startswith("Store"):
      A_s, B_s = _floats(ln)

  filename = os.path.join(csv_path, 'merged.csv')
  df = pd.read_csv(filename, index_col ="workload_id")
  workloads = get_workloads(df)
  # workloads.sort()
  # print(workloads)
  sd = get_slowdowns("LOCAL", "NUMA", sd_m, csv_path)
  dram_sd = get_slowdowns("LOCAL", "NUMA", dram_sd_m, csv_path)
  l3_sd = get_slowdowns("LOCAL", "NUMA", l3_sd_m, csv_path)
  l2_sd = get_slowdowns("LOCAL", "NUMA", l2_sd_m, csv_path)
  l1_sd = get_slowdowns("LOCAL", "NUMA", l1_sd_m, csv_path)
  store_sd = get_slowdowns("LOCAL", "NUMA", store_sd_m, csv_path)
  other = sd - dram_sd - l3_sd - l2_sd - l1_sd - store_sd

  cyc = [get_vals("cycles", configs[i], csv_path) for i in range(len(configs))]
  st_stall = [get_vals("EXE_ACTIVITY.BOUND_ON_STORES", configs[i], csv_path) for i in range(len(configs))]
  mem_any = [get_vals("CYCLE_ACTIVITY.STALLS_MEM_ANY", configs[i], csv_path) for i in range(len(configs))]
  l1_stall = [get_vals("CYCLE_ACTIVITY.STALLS_L1D_MISS", configs[i], csv_path) for i in range(len(configs))]
  l2_stall = [get_vals("CYCLE_ACTIVITY.STALLS_L2_MISS", configs[i], csv_path) for i in range(len(configs))]
  l3_stall = [get_vals("CYCLE_ACTIVITY.STALLS_L3_MISS", configs[i], csv_path) for i in range(len(configs))]

  l1_miss = [get_vals("MEM_LOAD_RETIRED.L1_MISS", configs[i], csv_path) for i in range(len(configs))]
  fb_hit = [get_vals("MEM_LOAD_RETIRED.FB_HIT", configs[i], csv_path) for i in range(len(configs))]
  pf_l1_any = [get_vals("OFFCORE_RESPONSE.PF_L1D_AND_SW.ANY_RESPONSE", configs[i], csv_path) for i in range(len(configs))]
  pf_l1_l3_hit = [get_vals("OFFCORE_RESPONSE.PF_L1D_AND_SW.L3_HIT.ANY_SNOOP", configs[i], csv_path) for i in range(len(configs))]
  demand_data_rd = [get_vals("OFFCORE_REQUESTS.DEMAND_DATA_RD", configs[i], csv_path) for i in range(len(configs))]
  outstanding_cyc_demand_rd = [get_vals("OFFCORE_REQUESTS_OUTSTANDING.CYCLES_WITH_DEMAND_DATA_RD", configs[i], csv_path) for i in range(len(configs))]

  aol = [outstanding_cyc_demand_rd[i]/demand_data_rd[i] for i in range(len(configs))]

  cache_pred = A_c * ((pf_l1_any[0] - pf_l1_l3_hit[0]) / pf_l1_any[0]) \
    * (fb_hit[0] / (fb_hit[0] + l1_miss[0])) \
    * (l1_stall[0] - l2_stall[0]) / cyc[0] + B_c
  demand_rd_pred = 1.0 / (A_d / aol[0] + B_d) * C_d * l3_stall[0] / cyc[0] + D_d
  store_pred = A_s * st_stall[0] / cyc[0] + B_s

  cache_corr, _ = pearsonr(l2_sd, cache_pred)
  demand_rd_corr, _ = pearsonr(dram_sd, demand_rd_pred)
  store_corr, _ = pearsonr(store_sd, store_pred)
  print(f"Cache Slowdown pearson correlation: {cache_corr:.4f}")
  print(f"Demand Read Slowdown pearson correlation: {demand_rd_corr:.4f}")
  print(f"Store Slowdown pearson correlation: {store_corr:.4f}")

  metrics_path = "csv-metrics"
  if not os.path.exists(metrics_path):
    os.makedirs(metrics_path)

  pd.DataFrame({
    "workload_name": workloads,
    "pf_l1_any": pf_l1_any[0], "pf_l1_l3_hit": pf_l1_l3_hit[0],
    "fb_hit": fb_hit[0], "l1_miss": l1_miss[0],
    "l1_stall": l1_stall[0], "l2_stall": l2_stall[0], "cyc": cyc[0],
    "actual_sd": l2_sd, "predicted_sd": cache_pred,
  }).to_csv(os.path.join(metrics_path, "cache_slowdown.csv"), index=False)

  pd.DataFrame({
    "workload_name": workloads,
    "aol": aol[0], "l3_stall": l3_stall[0], "cyc": cyc[0],
    "actual_sd": dram_sd, "predicted_sd": demand_rd_pred,
  }).to_csv(os.path.join(metrics_path, "demand_rd_slowdown.csv"), index=False)

  pd.DataFrame({
    "workload_name": workloads,
    "st_stall": st_stall[0], "cyc": cyc[0],
    "actual_sd": store_sd, "predicted_sd": store_pred,
  }).to_csv(os.path.join(metrics_path, "store_slowdown.csv"), index=False)

  output_path = "plots"
  isExist = os.path.exists(output_path)
  if not isExist:
    os.makedirs(output_path)

  draw_bars_b([store_sd, dram_sd, l3_sd, l2_sd, l1_sd, other], \
    workloads, output_path, "sd_breakdown", [0.17, 1.01], \
    "Workloads", "Slowdown", "Slowdown Breakdown")
  
  

if __name__ == "__main__":
  configs = ["LOCAL", "NUMA"]
  main(configs)
