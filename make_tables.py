#!/usr/bin/env python3
"""Aggregates results/raw_runs.csv into the manuscript tables (CSV + a
markdown summary). All gains are paired per seed:
  gain = 100 * (p99_base - p99_model) / p99_base,
with the base = VXLAN+ECMP at the same workload, seed, load and fabric."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")
CFG = json.load(open(os.path.join(HERE, "config.json")))
df = pd.read_csv(os.path.join(OUT, "raw_runs.csv"))
df["phi"] = df["phi"].fillna("")

def ci(x):
    x = np.asarray(x, float)
    return x.mean(), stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))

def fmt(m, h, d=1):
    return f"{m:.{d}f} ± {h:.{d}f}"

def paired_gain(base, other, metric="p99_fct_ms"):
    b = base.set_index("seed")[metric]; o = other.set_index("seed")[metric]
    return ci(100 * (b - o.loc[b.index]) / b)

md = []
main = df[df.exp == "main"]
NAMES = {"vxlan_ecmp": "VXLAN + ECMP (baseline)", "srv6_ecmp": "SRv6 + ECMP",
         "vxlan_steer": f"VXLAN + steering, per-flow entropy (φ = {CFG['vxlan_entropy_fidelity']})",
         "vxlan_steer_tun": "VXLAN + steering, per-tunnel pinning",
         "srv6_steer": "SRv6 + steering (explicit SID list)"}
WLN = {"all_to_all": "All-to-all", "incast": "Incast", "bursty": "Bursty many-to-many"}

# ---------------- Table 2: baseline vs SRv6 steering ---------------------
rows = []
for wl in ["all_to_all", "incast", "bursty"]:
    b = main[(main.workload == wl) & (main.model == "vxlan_ecmp")]
    s = main[(main.workload == wl) & (main.model == "srv6_steer")]
    r = {"workload": WLN[wl]}
    for tag, d in (("vxlan", b), ("srv6", s)):
        for met in ["p99_fct_ms", "p50_fct_ms", "mean_qdelay_ms", "spine_imbalance_pct"]:
            m, h = ci(d[met]); r[f"{tag}_{met}"] = m; r[f"{tag}_{met}_ci"] = h
    r["p99_gain_pct"], r["p99_gain_ci"] = paired_gain(b, s)
    r["qdelay_gain_pct"], r["qdelay_gain_ci"] = paired_gain(b, s, "mean_qdelay_ms")
    rows.append(r)
t2 = pd.DataFrame(rows); t2.to_csv(os.path.join(OUT, "table2_baseline.csv"), index=False)
md.append("## Table 2 – VXLAN+ECMP vs SRv6 steering, 100 % effective load (mean ± 95% CI, 30 seeds)")
md.append("| Workload | VXLAN p99 FCT (ms) | SRv6 p99 FCT (ms) | p99 gain (%) | VXLAN mean queue (ms) | SRv6 mean queue (ms) | VXLAN imbalance (%) | SRv6 imbalance (%) |")
md.append("|---|---|---|---|---|---|---|---|")
for r in rows:
    md.append(f"| {r['workload']} | {fmt(r['vxlan_p99_fct_ms'], r['vxlan_p99_fct_ms_ci'],2)} | {fmt(r['srv6_p99_fct_ms'], r['srv6_p99_fct_ms_ci'],2)} | {fmt(r['p99_gain_pct'], r['p99_gain_ci'])} | {fmt(r['vxlan_mean_qdelay_ms'], r['vxlan_mean_qdelay_ms_ci'],2)} | {fmt(r['srv6_mean_qdelay_ms'], r['srv6_mean_qdelay_ms_ci'],2)} | {fmt(r['vxlan_spine_imbalance_pct'], r['vxlan_spine_imbalance_pct_ci'])} | {fmt(r['srv6_spine_imbalance_pct'], r['srv6_spine_imbalance_pct_ci'])} |")

# ---------------- Table 3: four-way (+ tunnel) ablation ------------------
rows = []
for m in ["vxlan_ecmp", "srv6_ecmp", "vxlan_steer_tun", "vxlan_steer", "srv6_steer"]:
    r = {"model": NAMES[m]}
    for wl in ["all_to_all", "incast", "bursty"]:
        b = main[(main.workload == wl) & (main.model == "vxlan_ecmp")]
        o = main[(main.workload == wl) & (main.model == m)]
        r[f"{wl}_gain"], r[f"{wl}_gain_ci"] = paired_gain(b, o)
        R = o["realizability"].dropna()
        r[f"{wl}_R"] = R.mean() if len(R) else np.nan
    rows.append(r)
t3 = pd.DataFrame(rows); t3.to_csv(os.path.join(OUT, "table3_ablation.csv"), index=False)
md.append("\n## Table 3 – Ablation: p99 FCT gain vs VXLAN+ECMP (paired, mean ± 95% CI) and path realizability R")
md.append("| Model | A2A gain | A2A R | Incast gain | Incast R | Bursty gain | Bursty R |")
md.append("|---|---|---|---|---|---|---|")
for r in rows:
    f = lambda x: "–" if np.isnan(x) else f"{x:.3f}"
    md.append(f"| {r['model']} | {fmt(r['all_to_all_gain'], r['all_to_all_gain_ci'])} | {f(r['all_to_all_R'])} | {fmt(r['incast_gain'], r['incast_gain_ci'])} | {f(r['incast_R'])} | {fmt(r['bursty_gain'], r['bursty_gain_ci'])} | {f(r['bursty_R'])} |")

# ---------------- Table 3b: realization-fidelity sweep --------------------
ph = df[df.exp == "phi"]
rows = []
for wl in ["all_to_all", "bursty"]:
    b = main[(main.workload == wl) & (main.model == "vxlan_ecmp")]
    s = main[(main.workload == wl) & (main.model == "srv6_steer")]
    sg = paired_gain(b, s)
    for p in sorted(ph.phi.unique(), key=float):
        o = ph[(ph.workload == wl) & (ph.phi == p)]
        g = paired_gain(b, o)
        # substrate gap: SRv6 steer minus VXLAN steer, paired
        gap = ci(100 * (o.set_index("seed").p99_fct_ms - s.set_index("seed").p99_fct_ms.loc[o.seed.values]) / b.set_index("seed").p99_fct_ms.loc[o.seed.values])
        rows.append({"workload": WLN[wl], "phi": float(p), "R": o.realizability.mean(),
                     "vxlan_steer_gain": g[0], "vxlan_steer_gain_ci": g[1],
                     "srv6_steer_gain": sg[0], "srv6_steer_gain_ci": sg[1],
                     "substrate_gap_pp": gap[0], "substrate_gap_ci": gap[1]})
t3b = pd.DataFrame(rows); t3b.to_csv(os.path.join(OUT, "table3b_fidelity_sweep.csv"), index=False)
md.append("\n## Table 3b – VXLAN entropy-steering fidelity φ sweep (substrate gap = SRv6 steer gain − VXLAN steer gain, pp)")
md.append("| Workload | φ | R | VXLAN steer gain (%) | SRv6 steer gain (%) | Gap (pp) |")
md.append("|---|---|---|---|---|---|")
for r in rows:
    md.append(f"| {r['workload']} | {r['phi']:.1f} | {r['R']:.3f} | {fmt(r['vxlan_steer_gain'], r['vxlan_steer_gain_ci'])} | {fmt(r['srv6_steer_gain'], r['srv6_steer_gain_ci'])} | {fmt(r['substrate_gap_pp'], r['substrate_gap_ci'])} |")

# ---------------- Table 4: load sweep -------------------------------------
ld = pd.concat([main.assign(load=100), df[df.exp == "load"]])
rows = []
for wl in ["all_to_all", "incast", "bursty"]:
    for L in [100, 110, 120, 130, 142]:
        b = ld[(ld.workload == wl) & (ld.model == "vxlan_ecmp") & (ld.load == L)]
        s = ld[(ld.workload == wl) & (ld.model == "srv6_steer") & (ld.load == L)]
        v = ld[(ld.workload == wl) & (ld.model == "vxlan_steer") & (ld.load == L)]
        g = paired_gain(b, s); gv = paired_gain(b, v)
        import prsim
        rho = np.mean([prsim.offered_utilisation(CFG, wl, sd, L) for sd in range(1, CFG["seeds"] + 1)])
        rows.append({"workload": WLN[wl], "load_pct": L, "rho_uplink": rho,
                     "vxlan_p99": ci(b.p99_fct_ms)[0], "vxlan_p99_ci": ci(b.p99_fct_ms)[1],
                     "srv6_p99": ci(s.p99_fct_ms)[0], "srv6_p99_ci": ci(s.p99_fct_ms)[1],
                     "srv6_gain": g[0], "srv6_gain_ci": g[1],
                     "vxlan_steer_gain": gv[0], "vxlan_steer_gain_ci": gv[1]})
t4 = pd.DataFrame(rows); t4.to_csv(os.path.join(OUT, "table4_load.csv"), index=False)
md.append("\n## Table 4 – Load sweep (effective load = C_nom / C_eff)")
md.append("| Workload | Load (%) | ρ uplink | VXLAN+ECMP p99 (ms) | SRv6 steer p99 (ms) | SRv6 gain (%) | VXLAN steer φ gain (%) |")
md.append("|---|---|---|---|---|---|---|")
for r in rows:
    md.append(f"| {r['workload']} | {r['load_pct']} | {r['rho_uplink']:.2f} | {fmt(r['vxlan_p99'], r['vxlan_p99_ci'],2)} | {fmt(r['srv6_p99'], r['srv6_p99_ci'],2)} | {fmt(r['srv6_gain'], r['srv6_gain_ci'])} | {fmt(r['vxlan_steer_gain'], r['vxlan_steer_gain_ci'])} |")

# ---------------- Table 5: segment depth ----------------------------------
sg = pd.concat([main[(main.workload == "all_to_all") & (main.model == "srv6_steer")].assign(segs=1),
                df[df.exp == "segs"]])
b = main[(main.workload == "all_to_all") & (main.model == "vxlan_ecmp")]
P = CFG["payload_bytes"]
rows = []
for g_ in [1, 2, 4, 6]:
    s = sg[sg.segs == g_]
    h = 14 + 40 + 8 + 16 * g_
    gg = paired_gain(b, s)
    rows.append({"segments": g_, "header_bytes": h, "header_overhead_pct": 100 * h / (P + h),
                 "payload_efficiency": P / (P + h), "srv6_p99": s.p99_fct_ms.mean(),
                 "gain": gg[0], "gain_ci": gg[1]})
t5 = pd.DataFrame(rows); t5.to_csv(os.path.join(OUT, "table5_segments.csv"), index=False)
md.append(f"\n## Table 5 – Segment depth, all-to-all, 100 % load (VXLAN header = 50 B → {100*50/(P+50):.2f} % overhead)")
md.append("| Segments | Header (B) | Header overhead (%) | Payload efficiency | SRv6 p99 (ms) | p99 gain vs VXLAN+ECMP (%) |")
md.append("|---|---|---|---|---|---|")
for r in rows:
    md.append(f"| {r['segments']} | {r['header_bytes']} | {r['header_overhead_pct']:.2f} | {r['payload_efficiency']:.3f} | {r['srv6_p99']:.2f} | {fmt(r['gain'], r['gain_ci'])} |")

# ---------------- Table 6: degraded uplink --------------------------------
dg = df[df.exp == "degraded"]
rows = []
for wl in ["all_to_all", "incast", "bursty"]:
    b = dg[(dg.workload == wl) & (dg.model == "vxlan_ecmp")]
    r = {"workload": WLN[wl], "vxlan_p99": b.p99_fct_ms.mean()}
    for m in ["vxlan_steer", "srv6_steer"]:
        o = dg[(dg.workload == wl) & (dg.model == m)]
        r[m + "_gain"], r[m + "_gain_ci"] = paired_gain(b, o)
        r[m + "_p99"] = o.p99_fct_ms.mean()
    rows.append(r)
t6 = pd.DataFrame(rows); t6.to_csv(os.path.join(OUT, "table6_degraded.csv"), index=False)
md.append("\n## Table 6 – One leaf–spine link pair at 50 % capacity")
md.append("| Workload | VXLAN+ECMP p99 (ms) | VXLAN steer φ p99 | gain (%) | SRv6 steer p99 | gain (%) |")
md.append("|---|---|---|---|---|---|")
for r in rows:
    md.append(f"| {r['workload']} | {r['vxlan_p99']:.2f} | {r['vxlan_steer_p99']:.2f} | {fmt(r['vxlan_steer_gain'], r['vxlan_steer_gain_ci'])} | {r['srv6_steer_p99']:.2f} | {fmt(r['srv6_steer_gain'], r['srv6_steer_gain_ci'])} |")

open(os.path.join(OUT, "summary.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))
