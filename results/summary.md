## Table 2 – VXLAN+ECMP vs SRv6 steering, 100 % effective load (mean ± 95% CI, 30 seeds)
| Workload | VXLAN p99 FCT (ms) | SRv6 p99 FCT (ms) | p99 gain (%) | VXLAN mean queue (ms) | SRv6 mean queue (ms) | VXLAN imbalance (%) | SRv6 imbalance (%) |
|---|---|---|---|---|---|---|---|
| All-to-all | 10.21 ± 0.10 | 9.20 ± 0.02 | 9.8 ± 0.8 | 4.61 ± 0.02 | 4.44 ± 0.01 | 7.0 ± 0.8 | 0.7 ± 0.1 |
| Incast | 2.17 ± 0.13 | 2.16 ± 0.12 | 0.5 ± 1.4 | 0.69 ± 0.02 | 0.70 ± 0.02 | 14.1 ± 1.8 | 5.6 ± 0.8 |
| Bursty many-to-many | 4.53 ± 0.41 | 3.57 ± 0.28 | 20.3 ± 3.5 | 1.03 ± 0.09 | 0.83 ± 0.07 | 14.1 ± 1.8 | 5.9 ± 0.6 |

## Table 3 – Ablation: p99 FCT gain vs VXLAN+ECMP (paired, mean ± 95% CI) and path realizability R
| Model | A2A gain | A2A R | Incast gain | Incast R | Bursty gain | Bursty R |
|---|---|---|---|---|---|---|
| VXLAN + ECMP (baseline) | 0.0 ± 0.0 | – | 0.0 ± 0.0 | – | 0.0 ± 0.0 | – |
| SRv6 + ECMP | -0.7 ± 0.0 | – | -1.1 ± 0.4 | – | -1.2 ± 0.4 | – |
| VXLAN + steering, per-tunnel pinning | -62.5 ± 2.5 | 0.565 | 0.7 ± 1.8 | 0.659 | 11.0 ± 3.8 | 0.814 |
| VXLAN + steering, per-flow entropy (φ = 0.7) | 4.6 ± 1.0 | 0.856 | 1.1 ± 1.2 | 0.868 | 15.5 ± 3.6 | 0.852 |
| SRv6 + steering (explicit SID list) | 9.8 ± 0.8 | 1.000 | 0.5 ± 1.4 | 1.000 | 20.3 ± 3.5 | 1.000 |

## Table 3b – VXLAN entropy-steering fidelity φ sweep (substrate gap = SRv6 steer gain − VXLAN steer gain, pp)
| Workload | φ | R | VXLAN steer gain (%) | SRv6 steer gain (%) | Gap (pp) |
|---|---|---|---|---|---|
| All-to-all | 0.5 | 0.759 | 2.2 ± 0.9 | 9.8 ± 0.8 | 7.5 ± 0.7 |
| All-to-all | 0.6 | 0.807 | 2.8 ± 1.0 | 9.8 ± 0.8 | 7.0 ± 0.8 |
| All-to-all | 0.7 | 0.856 | 4.6 ± 1.0 | 9.8 ± 0.8 | 5.2 ± 0.7 |
| All-to-all | 0.8 | 0.905 | 6.5 ± 1.0 | 9.8 ± 0.8 | 3.2 ± 0.6 |
| All-to-all | 0.9 | 0.952 | 7.6 ± 0.8 | 9.8 ± 0.8 | 2.2 ± 0.4 |
| All-to-all | 1.0 | 1.000 | 10.4 ± 0.8 | 9.8 ± 0.8 | -0.6 ± 0.0 |
| Bursty many-to-many | 0.5 | 0.752 | 11.9 ± 3.7 | 20.3 ± 3.5 | 8.4 ± 2.1 |
| Bursty many-to-many | 0.6 | 0.801 | 13.2 ± 3.6 | 20.3 ± 3.5 | 7.1 ± 1.9 |
| Bursty many-to-many | 0.7 | 0.852 | 15.5 ± 3.6 | 20.3 ± 3.5 | 4.9 ± 1.8 |
| Bursty many-to-many | 0.8 | 0.901 | 17.1 ± 3.5 | 20.3 ± 3.5 | 3.3 ± 1.7 |
| Bursty many-to-many | 0.9 | 0.950 | 18.5 ± 3.4 | 20.3 ± 3.5 | 1.8 ± 1.8 |
| Bursty many-to-many | 1.0 | 1.000 | 21.3 ± 3.1 | 20.3 ± 3.5 | -1.0 ± 1.1 |

## Table 4 – Load sweep (effective load = C_nom / C_eff)
| Workload | Load (%) | ρ uplink | VXLAN+ECMP p99 (ms) | SRv6 steer p99 (ms) | SRv6 gain (%) | VXLAN steer φ gain (%) |
|---|---|---|---|---|---|---|
| All-to-all | 100 | 0.67 | 10.21 ± 0.10 | 9.20 ± 0.02 | 9.8 ± 0.8 | 4.6 ± 1.0 |
| All-to-all | 110 | 0.74 | 11.25 ± 0.11 | 10.13 ± 0.03 | 9.9 ± 0.9 | 4.8 ± 1.0 |
| All-to-all | 120 | 0.81 | 12.41 ± 0.14 | 11.05 ± 0.03 | 10.9 ± 1.0 | 5.8 ± 1.2 |
| All-to-all | 130 | 0.87 | 14.07 ± 0.24 | 11.98 ± 0.03 | 14.7 ± 1.4 | 8.9 ± 1.7 |
| All-to-all | 142 | 0.95 | 18.71 ± 0.60 | 13.26 ± 0.06 | 28.6 ± 2.2 | 17.8 ± 2.7 |
| Incast | 100 | 0.17 | 2.17 ± 0.13 | 2.16 ± 0.12 | 0.5 ± 1.4 | 1.1 ± 1.2 |
| Incast | 110 | 0.19 | 2.45 ± 0.15 | 2.44 ± 0.14 | 0.2 ± 1.5 | 1.1 ± 1.5 |
| Incast | 120 | 0.21 | 2.75 ± 0.18 | 2.74 ± 0.16 | 0.4 ± 1.4 | 1.5 ± 1.6 |
| Incast | 130 | 0.22 | 3.07 ± 0.21 | 3.05 ± 0.18 | 0.2 ± 1.6 | 1.2 ± 1.8 |
| Incast | 142 | 0.24 | 3.47 ± 0.24 | 3.45 ± 0.21 | 0.2 ± 1.7 | 1.8 ± 1.9 |
| Bursty many-to-many | 100 | 0.56 | 4.53 ± 0.41 | 3.57 ± 0.28 | 20.3 ± 3.5 | 15.5 ± 3.6 |
| Bursty many-to-many | 110 | 0.62 | 5.58 ± 0.58 | 4.42 ± 0.41 | 19.6 ± 3.7 | 15.9 ± 4.0 |
| Bursty many-to-many | 120 | 0.68 | 6.74 ± 0.77 | 5.38 ± 0.57 | 19.1 ± 3.5 | 15.2 ± 3.5 |
| Bursty many-to-many | 130 | 0.73 | 8.08 ± 0.99 | 6.55 ± 0.77 | 18.2 ± 3.5 | 15.1 ± 3.6 |
| Bursty many-to-many | 142 | 0.80 | 9.82 ± 1.26 | 8.00 ± 0.99 | 18.0 ± 2.9 | 15.6 ± 3.3 |

## Table 5 – Segment depth, all-to-all, 100 % load (VXLAN header = 50 B → 1.21 % overhead)
| Segments | Header (B) | Header overhead (%) | Payload efficiency | SRv6 p99 (ms) | p99 gain vs VXLAN+ECMP (%) |
|---|---|---|---|---|---|
| 1 | 78 | 1.87 | 0.981 | 9.20 | 9.8 ± 0.8 |
| 2 | 94 | 2.24 | 0.978 | 9.24 | 9.4 ± 0.8 |
| 4 | 126 | 2.98 | 0.970 | 9.31 | 8.7 ± 0.9 |
| 6 | 158 | 3.71 | 0.963 | 9.38 | 8.0 ± 0.9 |

## Table 6 – One leaf–spine link pair at 50 % capacity
| Workload | VXLAN+ECMP p99 (ms) | VXLAN steer φ p99 | gain (%) | SRv6 steer p99 | gain (%) |
|---|---|---|---|---|---|
| All-to-all | 53.01 | 13.55 | 74.3 ± 0.9 | 11.04 | 79.0 ± 0.8 |
| Incast | 2.71 | 2.21 | 15.5 ± 5.0 | 2.22 | 15.4 ± 4.8 |
| Bursty many-to-many | 13.33 | 5.19 | 58.4 ± 4.9 | 4.79 | 61.8 ± 4.5 |
