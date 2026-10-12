#!/usr/bin/env python3
"""Store-and-forward vs cut-through sensitivity (30 seeds, same routing)."""
import os, sys, json, numpy as np
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.argv = ["x"]
src = open(os.path.join(HERE, "verify_prsim.py")).read()
exec(src.split("# ---------------------------------------------------------------- V1")[0].replace("__file__", repr(os.path.join(HERE, "verify_prsim.py"))))
exec(src.split("# ---------------------------------------------------------------- V1")[1].split("for wl, model in")[0])
out = {}
for wl in ["all_to_all", "incast", "bursty"]:
    G = []
    for sd in range(1, 31):
        r = {}
        for m in ["vxlan_ecmp", "vxlan_steer", "srv6_steer"]:
            fab, flows, tr = traced(wl, m, sd)
            r[m] = (np.percentile(tr["fct"], 99), np.percentile(reference_fct(fab, flows, tr, store_forward=True)[0], 99))
        g = lambda m, j: 100 * (r["vxlan_ecmp"][j] - r[m][j]) / r["vxlan_ecmp"][j]
        G.append([g("srv6_steer", 0), g("srv6_steer", 1), g("vxlan_steer", 1), g("srv6_steer", 1) - g("vxlan_steer", 1)])
    G = np.array(G); h = stats.t.ppf(.975, 29) * G.std(0, ddof=1) / np.sqrt(30)
    out[wl] = {k: [round(m, 1), round(e, 1)] for k, m, e in zip(["srv6_cut_through", "srv6_store_forward", "vxlan_steer_store_forward", "gap_store_forward_pp"], G.mean(0), h)}
    print(wl, out[wl])
json.dump(out, open(os.path.join(HERE, "sf_sensitivity.json"), "w"), indent=1)
