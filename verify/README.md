# Pre-submission verification of prsim

```bash
python3 verify/verify_prsim.py      # 23 checks → verification_log.txt, verification_report.json
python3 verify/sf_sensitivity.py    # store-and-forward sensitivity → sf_sensitivity.json
```

| Check | What it tests | Result |
|---|---|---|
| V1 (9 cases) | An independent fixed-point solver, which does not use prsim's event loop, recomputes every flow's completion time from prsim's paths | Exact match (≤ 4e-18 s). Rare exact arrival ties may be served in either order; p99 is unaffected |
| V2 (6 cases, 142 % load) | No overlapping service on any link; FIFO order; FCT ≥ serialization bound; byte conservation | Pass |
| V3 | Each of 11,040 steering decisions is re-derived as the argmin of Eq. (3); SRv6 realizes every intent | Pass (0 non-optimal) |
| V4 | Main gains with 100 seeds vs 30 | All inside the 30-seed CIs (9.7 / −0.0 / 20.1 % vs 9.8 / 0.5 / 20.3 %) |
| V6 | Table aggregates recomputed from raw_runs.csv with plain numpy | Match (≤ 4e-15) |
| V5 / sf_sensitivity | Same runs and routing decisions re-solved under store-and-forward | All-to-all robust (8.8 vs 9.8 %). **Bursty is model-sensitive (9.3 vs 20.3 %; substrate gap 0.4 ± 2.2 pp)**; disclosed in manuscript §6.3 |
