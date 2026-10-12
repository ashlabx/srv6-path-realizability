#!/usr/bin/env python3
"""Independent verification battery for prsim (pre-submission check).

V1  Independent queueing engine: recompute every flow's FCT from prsim's
    realized paths with a separately written fixed-point solver (no event
    heap), and compare to prsim.
V2  Physical invariants: per-link busy intervals never overlap, each link
    serves in FIFO order of head arrival, FCT >= serialization lower bound,
    bytes are conserved.
V3  Controller check: every steering decision is re-derived from the logged
    state and must equal the argmin of Eq. (3).
V4  Statistical stability: main-table gains with 100 seeds vs 30 seeds.
V5  Model-choice sensitivity: store-and-forward instead of cut-through.
V6  Table recomputation: every aggregate in results/*.csv recomputed from
    raw_runs.csv with plain numpy.
"""
import json, os, sys, itertools
import numpy as np, pandas as pd
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import prsim
CFG = json.load(open(os.path.join(ROOT, "config.json")))
OK = []
def check(name, cond, detail=""):
    OK.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))

def traced(wl, model, seed, load=100.0, phi=None):
    fab = prsim.build_fabric(CFG, load)
    flows = prsim.WORKLOADS[wl](fab, np.random.default_rng([seed, 1]), CFG["workloads"][wl])
    tr = {}
    prsim.simulate(fab, flows, model, np.random.default_rng([seed, 2]), CFG,
                   phi=CFG["vxlan_entropy_fidelity"] if phi is None else phi, trace=tr)
    return fab, flows, tr

# ---------------------------------------------------------------- V1
def reference_fct(fab, flows, tr, store_forward=False, tie_rank=None):
    """Fixed-point solver: iterate per-link FIFO schedules until head-arrival
    times stop changing. Written independently of prsim's event loop."""
    n = len(flows); prop = tr["prop"]; W = tr["wbytes"]; paths = tr["path"]
    arr = [[flows[i][0]] + [None] * (len(paths[i]) - 1) for i in range(n)]
    start = [[0.0] * len(paths[i]) for i in range(n)]
    fin = [[0.0] * len(paths[i]) for i in range(n)]
    for it in range(200):
        for i in range(n):          # propagate tentative arrivals
            for k in range(1, len(paths[i])):
                if arr[i][k] is None:
                    arr[i][k] = arr[i][k - 1] + prop
        per_link = {}
        for i in range(n):
            for k, l in enumerate(paths[i]):
                per_link.setdefault(l, []).append((arr[i][k], i, k))
        for l, lst in per_link.items():
            lst.sort()
        # schedule hop by hop in increasing hop index so upstream finishes are known
        changed = False
        busy = {l: 0.0 for l in per_link}
        # process all (arrival, i, k) globally in arrival order
        rk = (lambda i, k: tie_rank.get((i, k), 0)) if tie_rank else (lambda i, k: 0)
        events = [(a, i, k) for (a, r, i, k) in sorted((round(a, 15), rk(i, k), i, k) for l in per_link for (a, i, k) in per_link[l])]
        events = [(arr[i][k], i, k) for (_, i, k) in events]
        for a, i, k in events:
            l = paths[i][k]
            s = max(a, busy[l])
            f = s + W[i] * 8 / fab.cap[l]
            if k > 0:
                f = max(f, fin[i][k - 1] + prop)
            busy[l] = f
            start[i][k], fin[i][k] = s, f
            if k + 1 < len(paths[i]):
                na = (f if store_forward else s) + prop
                if arr[i][k + 1] is None or abs(na - arr[i][k + 1]) > 1e-15:
                    arr[i][k + 1] = na; changed = True
        if not changed:
            break
    return np.array([fin[i][-1] - flows[i][0] for i in range(n)]), it

for wl, model in itertools.product(["all_to_all", "incast", "bursty"], ["vxlan_ecmp", "vxlan_steer", "srv6_steer"]):
    fab, flows, tr = traced(wl, model, 3)
    ref, its = reference_fct(fab, flows, tr)
    n_diff = int((np.abs(ref - tr["fct"]) > 1e-9).sum())
    # Exact ties in head arrival (identical float times) may be served in either
    # order by a FIFO link. Re-solve with prsim's tie order to confirm that ties
    # are the only source of difference; this must then match exactly.
    tie_rank = {(i, k): n for n, (i, k, *_ ) in enumerate(tr["hops"])}
    ref2, _ = reference_fct(fab, flows, tr, tie_rank=tie_rank)
    err = np.max(np.abs(ref2 - tr["fct"]))
    p99_err = abs(np.percentile(ref, 99) - np.percentile(tr["fct"], 99))
    check(f"V1 independent engine matches prsim ({wl}, {model})", err < 1e-9,
          f"exact match with same tie order (max |Δ| {err:.1e} s); with arbitrary tie order {n_diff} flow(s) differ, p99 |Δ| {p99_err:.1e} s")

# ---------------------------------------------------------------- V2
for wl, model in itertools.product(["all_to_all", "incast", "bursty"], ["vxlan_ecmp", "srv6_steer"]):
    fab, flows, tr = traced(wl, model, 5, load=142)
    hops = pd.DataFrame(tr["hops"], columns=["i", "hop", "link", "arr", "s", "f", "W"])
    overlap, fifo = 0, 0
    for l, g in hops.groupby("link"):
        g = g.sort_values("s")
        overlap += int((g.s.values[1:] < g.f.values[:-1] - 1e-12).sum())
        fifo += int((np.diff(g.arr.values) < -1e-12).sum())
    lb = np.array([tr["wbytes"][i] * 8 / min(fab.cap[l] for l in tr["path"][i]) + (len(tr["path"][i]) - 1) * tr["prop"]
                   for i in range(len(flows))])
    below = int((tr["fct"] < lb - 1e-12).sum())
    served = hops.groupby("i").W.sum().values
    expect = np.array([tr["wbytes"][i] * len(tr["path"][i]) for i in sorted(hops.i.unique())])
    check(f"V2 invariants ({wl}, {model}, 142% load)", overlap == 0 and fifo == 0 and below == 0 and np.allclose(served, expect),
          f"overlaps={overlap}, FIFO violations={fifo}, FCT<bound={below}")

# ---------------------------------------------------------------- V3
bad = total = 0
for wl, model in itertools.product(["all_to_all", "bursty", "incast"], ["srv6_steer", "vxlan_steer", "vxlan_steer_tun"]):
    fab, flows, tr = traced(wl, model, 7)
    for (i, t, ls, ld, W, best, bestv, free, ledger) in tr["decisions"]:
        vals = []
        for s in range(fab.S):
            up, dn = fab.idx[("l2s", ls, s)], fab.idx[("s2l", s, ld)]
            vals.append(max(max(free[up], t) + (ledger[up] + W) * 8 / fab.cap[up],
                            max(free[dn], t) + (ledger[dn] + W) * 8 / fab.cap[dn]))
        total += 1
        bad += int(vals[best] > min(vals) + 1e-12)
    if model == "srv6_steer":
        r = tr["realised"]; m = tr["intended"] >= 0
        check(f"V3 SRv6 realizes every intent ({wl})", np.all(r[m] == tr["intended"][m]))
check("V3 every steering decision is the argmin of Eq. (3)", bad == 0, f"{bad} of {total} decisions not optimal")

# ---------------------------------------------------------------- V4
def gains(seeds, wl, model="srv6_steer"):
    g = []
    for sd in seeds:
        b = prsim.run_one(CFG, wl, "vxlan_ecmp", sd)["p99_fct_ms"]
        o = prsim.run_one(CFG, wl, model, sd)["p99_fct_ms"]
        g.append(100 * (b - o) / b)
    g = np.array(g); h = stats.t.ppf(.975, len(g) - 1) * g.std(ddof=1) / np.sqrt(len(g))
    return g.mean(), h
for wl in ["all_to_all", "incast", "bursty"]:
    m30, h30 = gains(range(1, 31), wl)
    m100, h100 = gains(range(1, 101), wl)
    check(f"V4 100-seed mean inside 30-seed CI ({wl})", abs(m100 - m30) <= h30,
          f"30 seeds {m30:.1f} ± {h30:.1f}; 100 seeds {m100:.1f} ± {h100:.1f}")

# ---------------------------------------------------------------- V5
for wl in ["all_to_all", "bursty"]:
    g_ct, g_sf = [], []
    for sd in range(1, 11):
        res = {}
        for model in ["vxlan_ecmp", "srv6_steer"]:
            fab, flows, tr = traced(wl, model, sd)
            res[model] = (np.percentile(tr["fct"], 99), np.percentile(reference_fct(fab, flows, tr, store_forward=True)[0], 99))
        g_ct.append(100 * (res["vxlan_ecmp"][0] - res["srv6_steer"][0]) / res["vxlan_ecmp"][0])
        g_sf.append(100 * (res["vxlan_ecmp"][1] - res["srv6_steer"][1]) / res["vxlan_ecmp"][1])
    print(f"INFO V5 {wl}: cut-through gain {np.mean(g_ct):.1f}%, store-and-forward gain {np.mean(g_sf):.1f}% "
          f"(10 seeds, same routing decisions)")

# ---------------------------------------------------------------- V6
raw = pd.read_csv(os.path.join(ROOT, "results", "raw_runs.csv"))
t2 = pd.read_csv(os.path.join(ROOT, "results", "table2_baseline.csv"))
main = raw[raw.exp == "main"]
worst = 0
for _, r in t2.iterrows():
    wl = {"All-to-all": "all_to_all", "Incast": "incast", "Bursty many-to-many": "bursty"}[r.workload]
    b = main[(main.workload == wl) & (main.model == "vxlan_ecmp")].sort_values("seed").p99_fct_ms.values
    s = main[(main.workload == wl) & (main.model == "srv6_steer")].sort_values("seed").p99_fct_ms.values
    worst = max(worst, abs(np.mean(100 * (b - s) / b) - r.p99_gain_pct))
t3 = pd.read_csv(os.path.join(ROOT, "results", "table3_ablation.csv"))
for i, m in enumerate(["vxlan_ecmp", "srv6_ecmp", "vxlan_steer_tun", "vxlan_steer", "srv6_steer"]):
    for wl in ["all_to_all", "incast", "bursty"]:
        b = main[(main.workload == wl) & (main.model == "vxlan_ecmp")].sort_values("seed").p99_fct_ms.values
        o = main[(main.workload == wl) & (main.model == m)].sort_values("seed").p99_fct_ms.values
        worst = max(worst, abs(np.mean(100 * (b - o) / b) - t3.loc[i, f"{wl}_gain"]))
check("V6 table aggregates recomputed from raw runs", worst < 1e-9, f"max |Δ| = {worst:.1e}")

n_fail = sum(1 for _, ok, _ in OK if not ok)
print(f"\n{len(OK) - n_fail}/{len(OK)} checks passed")
json.dump([dict(check=a, passed=b, detail=c) for a, b, c in OK], open(os.path.join(HERE, "verification_report.json"), "w"), indent=1)
