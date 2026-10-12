#!/usr/bin/env python3
"""Approximate 30-draw re-run of the original four-way ablation with the
reconstructed model. The original steering rule was not recoverable, so both
steered modes use a random equal split of flows across spines. The result is
indicative only."""
import random, numpy as np
from scipy import stats
import reconstruct_original_model as o

def run(flows, spines, sub, factor=1.0):
    free, fct = {}, []
    for i in sorted(range(len(flows)), key=lambda i: flows[i][3]):
        s, d, mb, st = flows[i]; t = st * 1000; hop = mb / (o.CAP * o.EFF[sub]) * 1000 * factor
        l1, l2 = (o.LEAF[s], spines[i]), (spines[i], o.LEAF[d])
        b1 = max(t, free.get(l1, 0)); e1 = b1 + hop; free[l1] = e1
        b2 = max(e1, free.get(l2, 0)); e2 = b2 + hop; free[l2] = e2
        fct.append(e2 - t + 0.25)
    return np.percentile(fct, 99)

for w in ["all_to_all", "incast", "bursty_many_to_many"]:
    fl = o.workload(w); R = []
    for seed in range(1, 31):
        g = random.Random(5000 + seed); ecmp = [g.choice(["sp1", "sp2"]) for _ in fl]
        bal = ["sp1", "sp2"] * (len(fl) // 2); g.shuffle(bal)
        b = run(fl, ecmp, "vxlan"); G = lambda x: 100 * (b - x) / b
        vp, sp = G(run(fl, bal, "vxlan", 0.95)), G(run(fl, bal, "srv6", 0.9))
        vp0, sp0 = G(run(fl, bal, "vxlan")), G(run(fl, bal, "srv6"))
        R.append((vp, sp, sp - vp, vp0, sp0, sp0 - vp0))
    R = np.array(R); h = stats.t.ppf(.975, 29) * R.std(0, ddof=1) / np.sqrt(30)
    names = ["VXLAN steer (x0.95)", "SRv6 steer (x0.9)", "gap", "VXLAN steer (no factor)", "SRv6 steer (no factor)", "gap (no factor)"]
    print(w); [print(f"  {n:24s} {m:6.1f} ± {e:.1f}") for n, m, e in zip(names, R.mean(0), h)]
