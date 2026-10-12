# Small Linux Realizability Artifact

This artifact is a **minimal Linux namespace-based realizability check** for the paper.

It is intentionally small. The goal is **not** to reproduce the full simulation study or to claim production dataplane performance.
Instead, it demonstrates that:

1. a VXLAN-based virtualized fabric can be realized in Linux,
2. an SRv6-based steered fabric can also be realized in Linux,
3. path/service intent can be expressed differently across the two substrates.

## Topology

- 2 spines: `sp1`, `sp2`
- 2 leafs: `lf1`, `lf2`
- 4 hosts: `h1`, `h2`, `h3`, `h4`
- 1 service node: `svc1`

Host placement:
- `h1`, `h2` on `lf1`
- `h3`, `h4` on `lf2`

## Addressing

### IPv4 underlay for VXLAN
- `lf1-sp1`: `10.0.11.1/30`, `10.0.11.2/30`
- `lf1-sp2`: `10.0.12.1/30`, `10.0.12.2/30`
- `lf2-sp1`: `10.0.21.1/30`, `10.0.21.2/30`
- `lf2-sp2`: `10.0.22.1/30`, `10.0.22.2/30`
- VTEPs:
  - `lf1`: `10.255.1.1/32`
  - `lf2`: `10.255.2.1/32`

### IPv6 underlay for SRv6
- `lf1-sp1`: `2001:db8:11::1/64`, `2001:db8:11::2/64`
- `lf1-sp2`: `2001:db8:12::1/64`, `2001:db8:12::2/64`
- `lf2-sp1`: `2001:db8:21::1/64`, `2001:db8:21::2/64`
- `lf2-sp2`: `2001:db8:22::1/64`, `2001:db8:22::2/64`

### Tenant subnet
- local bridge on `lf1`: `192.168.10.1/24`
- local bridge on `lf2`: `192.168.11.1/24`

Hosts:
- `h1`: `192.168.10.11/24`
- `h2`: `192.168.10.12/24`
- `h3`: `192.168.11.13/24`
- `h4`: `192.168.11.14/24`

## Requirements

- Ubuntu 22.04 or 24.04 recommended
- Kernel with SRv6 support (`sysctl net.ipv6.conf.all.seg6_enabled` should exist)
- Root access
- Tools:
  - `iproute2`
  - `iputils-ping`
  - `iperf3`
  - `tcpdump` (optional, for path verification)

Install example:
```bash
sudo apt-get update
sudo apt-get install -y iproute2 iputils-ping iperf3 tcpdump
```

## Quick start

### 1. Build the topology
```bash
sudo ./cleanup.sh
sudo ./create_topology.sh
```

### 2. VXLAN baseline demo
```bash
sudo ./setup_vxlan.sh
sudo ./validate_vxlan.sh
```

### 3. SRv6 steered demo
```bash
sudo ./cleanup.sh
sudo ./create_topology.sh
sudo ./setup_srv6.sh
sudo ./validate_srv6.sh
```

### 4. Optional traffic demo
```bash
sudo ./run_ping_tests.sh
sudo ./run_iperf_demo.sh
```

### 5. Cleanup
```bash
sudo ./cleanup.sh
```

## What this artifact proves

This artifact is designed only to show:
- Linux realization of both substrates,
- explicit substrate differences in how path/service intent is expressed,
- basic end-to-end connectivity and path verification.

It does **not** prove:
- production performance,
- ASIC dataplane cost,
- full control-plane feasibility,
- or the full simulation result set from the paper.
