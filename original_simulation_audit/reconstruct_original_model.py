#!/usr/bin/env python3
"""Reconstruction of the ORIGINAL (submitted-version) simulator, inferred from
its archived per-flow output (srv6_sim_results/per_flow_results.csv).

Recovered exactly:
  * workload arrival times: random.Random(7), start = uniform(0, 2) s per flow
    in (src, dst) generation order for all-to-all; incast = uniform(0, 0.8) s
  * link model: two inter-switch links (leaf->spine, spine->leaf), FIFO,
    store-and-forward, each hop takes size / (1000 MB/s * efficiency);
    FCT = serialization + queueing + 0.25 ms constant
  * efficiency: VXLAN 1/1.035 (3.5 % overhead), SRv6 1/1.015 (1.5 %)
  * an extra x0.9 multiplier on SRv6 serialization time
  * no host access links are modelled (incast receiver never queues)
  * SRv6 "programmable" spine assignment gives exactly equal flow counts per spine
Not recovered (RNG not identifiable): the per-flow ECMP spine draw and the
balanced SRv6 assignment. They are modelled here as a uniform random spine
(ECMP) and a random balanced permutation (SRv6).
"""
import random, sys
import numpy as np, pandas as pd

HOSTS = [f"h{i}" for i in range(1, 17)]
LEAF = {h: f"lf{(int(h[1:]) - 1) // 4 + 1}" for h in HOSTS}
CAP = 1000.0          # MB/s
EFF = {"vxlan": 1 / 1.035, "srv6": 1 / 1.015}
FIXED = 0.25          # ms

def workload(name):
    r = random.Random(7)
    fl = []
    if name == "all_to_all":
        for s in HOSTS:
            for d in HOSTS:
                if LEAF[s] != LEAF[d]:
                    fl.append((s, d, 64, r.uniform(0, 2)))
    elif name == "incast":
        for s in ["h1", "h2", "h3", "h5", "h6", "h7", "h9", "h10", "h11", "h13", "h14", "h15"]:
            fl.append((s, "h16", 32, r.uniform(0, 0.8)))
    elif name == "bursty_many_to_many":
        A, B = ["h1", "h2", "h3", "h4"], ["h9", "h10", "h11", "h12"]
        for k in range(5):
            for s in A + B:
                for d in (B if s in A else A):
                    fl.append((s, d, 48, 1.5 * k + r.uniform(0, 0.2)))
    return fl

def run(flows, spines, substrate, bonus=0.9):
    free, fct = {}, []
    order = sorted(range(len(flows)), key=lambda i: flows[i][3])
    for i in order:
        s, d, mb, st = flows[i]
        t = st * 1000.0
        hop = mb / (CAP * EFF[substrate]) * 1000.0
        if substrate == "srv6":
            hop *= bonus
        l1, l2 = (LEAF[s], spines[i]), (spines[i], LEAF[d])
        b1 = max(t, free.get(l1, 0.0)); e1 = b1 + hop; free[l1] = e1
        b2 = max(e1, free.get(l2, 0.0)); e2 = b2 + hop; free[l2] = e2
        fct.append(e2 - t + FIXED)
    return np.percentile(fct, 99)

def verify(path):
    """Feeds the archived spine choices back in; must reproduce archived p99."""
    df = pd.read_csv(path)
    for (w, m), x in df.groupby(["workload", "mode"]):
        fl = list(zip(x.src, x.dst, x.size_mb, x.start))
        p = run(fl, list(x.spine), "srv6" if m == "srv6_prog" else "vxlan")
        print(f"verify {w:22s} {m:10s} replica p99 {p:9.3f}  archived {np.percentile(x.fct_ms, 99):9.3f}")

if __name__ == "__main__":
    verify(sys.argv[1])
    rows = []
    for w in ["all_to_all", "incast", "bursty_many_to_many"]:
        fl = workload(w)
        for seed in range(1, 31):
            g = random.Random(1000 + seed)
            ecmp = [g.choice(["sp1", "sp2"]) for _ in fl]
            bal = ["sp1", "sp2"] * (len(fl) // 2); g.shuffle(bal)
            base = run(fl, ecmp, "vxlan")
            rows.append(dict(workload=w, seed=seed,
                             reported_model=100 * (base - run(fl, bal, "srv6")) / base,
                             no_bonus=100 * (base - run(fl, bal, "srv6", bonus=1.0)) / base,
                             bonus_only=100 * (base - run(fl, ecmp, "srv6")) / base,
                             base_p99=base))
    df = pd.DataFrame(rows)
    df.to_csv("original_model_30_seeds.csv", index=False)
    print(df.groupby("workload").agg(['mean', 'std', 'min', 'max']).round(1).T.to_string())
