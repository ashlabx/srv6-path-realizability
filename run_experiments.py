#!/usr/bin/env python3
"""Regenerates every quantitative result in the revised manuscript from
config.json. Output: results/raw_runs.csv (one row per run) and
results/table*.csv (aggregates: mean and 95 % t-interval over seeds; gains
are paired per seed against VXLAN+ECMP under identical workload and hash
draws)."""
import csv, json, os, sys, itertools
import numpy as np
from scipy import stats
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prsim

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "config.json")))
OUT = os.path.join(HERE, "results"); os.makedirs(OUT, exist_ok=True)
SEEDS = list(range(1, CFG["seeds"] + 1))
WLS = ["all_to_all", "incast", "bursty"]
MODELS = ["vxlan_ecmp", "srv6_ecmp", "vxlan_steer", "vxlan_steer_tun", "srv6_steer"]
LOADS = [100, 110, 120, 130, 142]
SEGS = [1, 2, 4, 6]
PHIS = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
DEGRADED = {"leaf": 0, "spine": 0, "factor": 0.5}

def job(args):
    exp, wl, model, seed, load, segs, phi, deg = args
    r = prsim.run_one(CFG, wl, model, seed, load, segs, phi,
                      DEGRADED if deg else None)
    r.update(dict(exp=exp, workload=wl, model=model, seed=seed, load=load,
                  segs=segs, phi=("" if phi is None else phi), degraded=int(deg)))
    return r

def jobs():
    J = []
    for wl, m, s in itertools.product(WLS, MODELS, SEEDS):          # E1, E2
        J.append(("main", wl, m, s, 100, 1, None, False))
    for wl, p, s in itertools.product(["all_to_all", "bursty"], PHIS, SEEDS):
        J.append(("phi", wl, "vxlan_steer", s, 100, 1, p, False))   # E3
    for wl, L, m, s in itertools.product(WLS, LOADS, ["vxlan_ecmp", "srv6_steer", "vxlan_steer"], SEEDS):
        if L != 100:
            J.append(("load", wl, m, s, L, 1, None, False))          # E4
    for g, s in itertools.product(SEGS, SEEDS):
        if g != 1:
            J.append(("segs", "all_to_all", "srv6_steer", s, 100, g, None, False))  # E5
    for wl, m, s in itertools.product(WLS, ["vxlan_ecmp", "vxlan_steer", "srv6_steer"], SEEDS):
        J.append(("degraded", wl, m, s, 100, 1, None, True))         # E6
    return J

def ci(x):
    x = np.asarray(x, float)
    m = x.mean()
    h = stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0
    return m, h

if __name__ == "__main__":
    with Pool() as p:
        rows = p.map(job, jobs(), chunksize=4)
    keys = ["exp", "workload", "model", "seed", "load", "segs", "phi", "degraded",
            "p99_fct_ms", "p50_fct_ms", "mean_fct_ms", "mean_qdelay_ms",
            "p99_qdelay_ms", "spine_imbalance_pct", "realizability", "n_flows"]
    with open(os.path.join(OUT, "raw_runs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for r in rows: w.writerow({k: r[k] for k in keys})
    print("runs:", len(rows))
