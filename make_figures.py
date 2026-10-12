#!/usr/bin/env python3
"""Figures for the revised manuscript (print, 300 dpi PNG)."""
import os
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")
BLUE, ORANGE, GREY, INK, MUTED = "#2a78d6", "#eb6834", "#8a8983", "#1f1f1e", "#5f5e5a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GREY,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#e6e5df", "grid.linewidth": 0.6})

# Figure 1: path realizability R -> p99 gain (phi sweep) with SRv6 point
t = pd.read_csv(os.path.join(R, "table3b_fidelity_sweep.csv"))
fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.6), sharey=False)
for ax, wl in zip(axes, ["All-to-all", "Bursty many-to-many"]):
    d = t[t.workload == wl]
    ax.errorbar(d.R, d.vxlan_steer_gain, yerr=d.vxlan_steer_gain_ci, color=BLUE, lw=2,
                marker="o", ms=5, capsize=2, label="VXLAN + steering (entropy, φ = 0.5…1.0)")
    s = d.iloc[0]
    ax.errorbar([1.0], [s.srv6_steer_gain], yerr=[s.srv6_steer_gain_ci], color=ORANGE,
                marker="D", ms=7, capsize=2, lw=0, elinewidth=1.5, label="SRv6 + steering (explicit SID)")
    ax.set_title(wl, fontsize=9, color=INK)
    ax.set_xlabel("Path realizability R")
    ax.set_xlim(0.73, 1.02)
axes[0].set_ylabel("p99 FCT gain vs\nVXLAN+ECMP (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=2, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.1, 1, 1))
fig.savefig(os.path.join(R, "fig1_realizability.png"), dpi=300)

# Figure 2: load sweep
t = pd.read_csv(os.path.join(R, "table4_load.csv"))
fig, axes = plt.subplots(1, 3, figsize=(6.6, 2.5))
for ax, wl in zip(axes, ["All-to-all", "Incast", "Bursty many-to-many"]):
    d = t[t.workload == wl]
    ax.errorbar(d.load_pct, d.srv6_gain, yerr=d.srv6_gain_ci, color=ORANGE, lw=2, marker="D",
                ms=4, capsize=2, label="SRv6 + steering")
    ax.errorbar(d.load_pct, d.vxlan_steer_gain, yerr=d.vxlan_steer_gain_ci, color=BLUE, lw=2,
                marker="o", ms=4, capsize=2, label="VXLAN + steering (φ = 0.7)")
    ax.axhline(0, color=GREY, lw=0.8)
    ax.set_title(wl, fontsize=9, color=INK)
    ax.set_xlabel("Effective load (%)")
    ax.set_xticks([100, 110, 120, 130, 142])
axes[0].set_ylabel("p99 FCT gain vs\nVXLAN+ECMP (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=2, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.1, 1, 1))
fig.savefig(os.path.join(R, "fig2_load.png"), dpi=300)
print("ok")
