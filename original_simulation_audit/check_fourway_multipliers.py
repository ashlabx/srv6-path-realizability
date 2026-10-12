#!/usr/bin/env python3
"""Checks the archived four-way (substrate vs steering) run for step multipliers.

In the incast workload of that run no flow ever queues (queue_ms_mean = 0 for
every mode), so each p99 equals factor * serialization + 0.25 ms exactly, and
the multiplier applied to each forwarding mode can be read off directly.
"""
import csv, os
here = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(here, "archived_outputs/substrate_vs_steering/substrate_vs_steering_summary.csv"))))
SER = {"vxlan": 2 * 32 / (1000 / 1.035) * 1000, "srv6": 2 * 32 / (1000 / 1.015) * 1000}  # ms, 32 MB, 2 hops
print(f"{'mode':12s} {'archived p99':>12s} {'queue':>6s} {'implied factor':>15s}")
for r in rows:
    if r["workload"] != "incast":
        continue
    sub = "srv6" if r["mode"].startswith("srv6") else "vxlan"
    f = (float(r["latency_ms_p99"]) - 0.25) / SER[sub]
    print(f"{r['mode']:12s} {float(r['latency_ms_p99']):12.3f} {float(r['queue_ms_mean']):6.1f} {f:15.4f}")
