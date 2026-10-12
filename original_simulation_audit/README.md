# Audit of the original (submitted-version) simulation

The original simulation code was not retained. `archived_outputs/` holds its archived results exactly as produced. `reconstruct_original_model.py` rebuilds the model from those results.

```bash
python3 reconstruct_original_model.py archived_outputs/per_flow_results.csv
```

## What the script does

1. **Verification.** It feeds the archived per-flow spine choices back into the reconstructed model. It reproduces all six archived p99 values exactly (see `reconstruction_log.txt`).
2. **Re-run over 30 random spine draws** → `original_model_30_seeds.csv`, with three variants per draw:
   - the model as originally run;
   - the same model without the 0.9 factor;
   - the 0.9 factor alone, with ECMP spines and no steering.

## Recovered model

| Element | Original model |
|---|---|
| Links that queue | leaf→spine and spine→leaf only; host links are not modelled |
| Link service | FIFO, store-and-forward; each hop takes size / (1000 MB/s × efficiency) |
| Constant | +0.25 ms per flow |
| Encapsulation efficiency | VXLAN 1/1.035, SRv6 1/1.015 |
| Steering time factors | **× 0.9 on SRv6 steered hop time**; in the four-way run also **× 0.95 on VXLAN steered hop time**; ECMP modes × 1.0 (undocumented; see below) |
| SRv6 "steering" | main run: spines assigned so that flow counts per spine are exactly equal, with no evidence of a state-aware decision; four-way run: rule not recoverable |
| ECMP | per-flow random spine (the exact RNG was not recoverable) |
| Arrivals | `random.Random(7)`; all-to-all start = uniform(0, 2) s in (src, dst) order, regenerated exactly |
| Repetitions | one run per configuration |

**The 0.9 and 0.95 factors.** The archived model includes a 0.9 multiplicative factor in the SRv6 steered condition, and in the four-way run a 0.95 factor in the VXLAN steered condition. I could not recover contemporaneous documentation establishing the specific rationale for these factors. They should therefore be treated as undocumented modelling assumptions rather than attributed to a particular implementation mechanism such as reduced processing or hash-lookup cost. Mathematically, SRv6 hop time = size / (C × 0.985) × 0.9, an effective rate of about 1.095 C. That is faster than line rate.

## Results over 30 random spine draws

p99 gain vs VXLAN+ECMP, mean ± 95 % CI:

| Workload | As originally modelled | Without the 0.9 factor | 0.9 factor alone |
|---|---|---|---|
| All-to-all | 22.9 ± 5.3 % (single runs range −14.1 % to +58.0 %) | 3.2 ± 6.5 % | 23.9 ± 1.2 % |
| Bursty many-to-many | 18.3 ± 3.8 % | 5.6 ± 4.2 % | 15.2 ± 0.3 % |
| Incast | 18.1 ± 6.8 % | 6.9 ± 7.8 % | 14.9 ± 0.3 % |

## The four-way (substrate vs steering) run

Run `check_fourway_multipliers.py`. In that run's incast workload no flow queues, so each archived p99 equals factor × serialization + 0.25 ms. The implied factors come out exactly as VXLAN ECMP 1.00, VXLAN steering **0.95**, SRv6 ECMP 1.00, SRv6 steering **0.90** (`fourway_multiplier_check.txt`). The published incast gains (5.0 % and 11.7 %) and their 6.7-pp "substrate" difference are therefore entirely these factors.

`fourway_rerun_approx.py` re-runs the four-way comparison over 30 spine draws. The original steering rule was not recoverable, so both steered modes use a random equal split, and the result is indicative only. For all-to-all, the SRv6-over-VXLAN steering gap is 12.5 ± 1.2 pp with the factors and 3.8 ± 0.4 pp without them. The remainder reflects the VXLAN/SRv6 overhead assumption (3.5 % vs 1.5 %).

## Traceability of submitted values

| Submitted value | Traceable to archived output? |
|---|---|
| Table 2 gains 19.6 / 35.7 / 32.4 % | Yes: `comparison_summary.csv` (single run) |
| Table 2 absolute latencies (248.6, 412.3, 389.7 ms …) | No: archived 569.6 / 91.3 / 462.1 ms |
| Table 3 steering values (19.2 / 5.0 / 49.6 / 11.7 %) | Yes: `archived_outputs/substrate_vs_steering/` (single seed; steered modes carry × 0.95 / × 0.9 factors) |
| Table 3 SRv6 + ECMP (12.1 / 8.3 %) | No: the same archive shows 3.2 / 1.9 % |
| Table 4 gains at 100 % / 142 % and 142 % latencies | Yes: `load_sweep_summary.csv` |
| Table 4 rows at 120 % / 130 % | No: archived loads are 76 / 100 / 117 / 142 % |
| Table 5 at 1 and 6 segments | Yes: `segment_depth_sensitivity.csv` |
| Table 5 at 2 and 4 segments | Partly: archived 32.0 / 31.7 % gains and 2.5 / 4.5 % overhead |
| "Spine imbalance 2–6 %" | Mislabelled: archived values are flow-count differences |

The revised manuscript uses none of these values. All of its results come from `prsim` in the parent folder.
