# Path-realizability study — reproducibility package (IJECE paper 42851, revision 1)

This package regenerates every number, table and figure in the revised manuscript
*"Path Realizability Under Contention: SRv6 as a Programmable Virtualization Substrate for AI-Scale Infrastructure."*

```
prsim.py              flow-level discrete-event simulator (single file, numpy only)
config.json           every simulation parameter used in the paper
run_experiments.py    runs the full grid (2,250 runs, ~30 s on 2 cores) -> results/raw_runs.csv
make_tables.py        aggregates -> results/table2..6*.csv and results/summary.md
make_figures.py       -> results/fig1_realizability.png, results/fig2_load.png
test_prsim.py         sanity tests (pytest)
verify/               independent verification battery (23 checks) + service-model sensitivity
linux_artifact/       Linux network-namespace realizability artifact (VXLAN and SRv6)
original_simulation_audit/  archived outputs of the submitted version's simulation + reconstruction/audit
```

## Reproduce

```bash
pip install numpy scipy pandas matplotlib pytest
python3 -m pytest -q test_prsim.py
python3 run_experiments.py && python3 make_tables.py && python3 make_figures.py
```
Results are deterministic for a given `config.json`: each seed fixes the workload
(`numpy` `default_rng([seed, 1])`) and the per-flow hash/fidelity draws
(`default_rng([seed, 2])`). Every forwarding model sees the same flows and hash draws
(common random numbers), so gains are paired per seed.

## Model (manuscript Section 4)

| Item | Value |
|---|---|
| Fabric | 4 leaves × 2 spines, 4 hosts per leaf (16 hosts); 100 Gb/s host links, 100 Gb/s leaf–spine links (2:1 leaf oversubscription) |
| Link model | every directed link (host→leaf, leaf→spine, spine→leaf, leaf→host) is a FIFO, non-preemptive server; flow-level serial service with cut-through; 1 µs propagation per hop |
| Encapsulation | wire bytes = payload × (P + h)/P, P = 4096 B; VXLAN h = 50 B; SRv6 h = 14 + 40 + 8 + 16n B (n = segments). Header cost is serialization only; no per-segment processing cost |
| All-to-all | 10 rounds, 12 ms apart; each host sends 4 MiB to each of the 12 hosts on remote leaves; release jitter U[0, 50 µs]; random destination order |
| Incast | 60 events, Poisson (mean 1 ms apart); random receiver; 8 senders drawn from remote leaves; 2 MiB each; jitter U[0, 20 µs] |
| Bursty many-to-many | 80 bursts, Poisson (mean 0.5 ms); 4 random senders × 4 random remote receivers; lognormal sizes, median 1 MiB, σ = 1, cap 32 MiB |
| Seeds | 30 per condition; mean ± 95 % Student-t interval |
| Metric | p99 flow completion time (FCT); gain = 100·(p99_base − p99_model)/p99_base, paired per seed |

### Forwarding models
All steered models use one controller: at a flow's release time it picks
spine σ* = argmin_s max(completion estimate on src-leaf→s, completion estimate on s→dst-leaf),
where each estimate = max(link free time, now) + (bytes the controller has already placed on that link and not yet served + this flow)/capacity.
The substrates differ **only** in how σ* is realised:

| Model | Realisation of σ* |
|---|---|
| `vxlan_ecmp` | none; per-flow hash of the outer 5-tuple |
| `srv6_ecmp` | none; per-flow hash of the IPv6 flow label (same hash draws) |
| `vxlan_steer` | outer UDP source-port entropy; lands on σ* with probability φ, otherwise on the hash result (φ = 0.7 by default; φ = 1 is idealised) |
| `vxlan_steer_tun` | per-tunnel underlay policy: one spine per (src leaf, dst leaf) per round/event/burst |
| `srv6_steer` | explicit SID list; always σ* |

**Path realizability** R = fraction of steered flows whose realised spine equals σ*.

**Effective load** L = 100 · C_nominal / C_effective (all link capacities are scaled by 100/L,
workload unchanged). `make_tables.py` also reports the offered utilisation of the leaf→spine
tier, ρ = 8 · Σ inter-leaf bytes / (T · Σ C_leaf→spine), with T = rounds × gap
(all-to-all) or the last release time (Poisson workloads).

## Linux artifact
See `linux_artifact/README.md`. `captured_outputs/` holds the logs cited in Section 6.
**Note:** in the captured SRv6 run, host-to-host pings failed (100 % loss) because the
original `setup_srv6.sh` installs SRv6 state in one direction only. `setup_srv6_bidir.sh`
and `gather_srv6_bidir_evidence.sh` (added in revision 1) install the return path and
capture SRH packets on both leaves; they have not yet been run and must be rerun on a
seg6-capable kernel before the host-to-host result is cited.
