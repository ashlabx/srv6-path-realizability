#!/usr/bin/env bash
# Revision-1 addition (UNVERIFIED in the authoring environment; run on Ubuntu
# 22.04/24.04 with seg6 support and archive the outputs).
# Run AFTER setup_srv6.sh. The original setup_srv6.sh installs SRv6 state only
# in the lf1 -> lf2 direction, so host-to-host pings fail (no return path;
# see captured_outputs/srv6/h1_to_h3_ping.txt). This script adds the reverse
# direction and removes the service-SID detour for h4, because End.DX4 on the
# service SID decapsulates and terminates the SID list (it cannot continue a
# chain; a true chain needs an SR proxy behaviour such as End.AD, which
# upstream Linux does not implement).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

for n in lf1 lf2; do
  ns "$n" "sysctl -w net.ipv4.conf.all.rp_filter=0 >/dev/null"
  ns "$n" "sysctl -w net.ipv4.conf.default.rp_filter=0 >/dev/null"
done

# lf1 delivery SIDs for h1 / h2
ns lf1 "ip -6 route replace 2001:db8:1001:1::11/128 encap seg6local action End.DX4 nh4 192.168.10.11 dev lo"
ns lf1 "ip -6 route replace 2001:db8:1001:1::12/128 encap seg6local action End.DX4 nh4 192.168.10.12 dev lo"

# lf2 -> lf1 steered routes (explicit egress spine per destination)
ns lf2 "ip route replace 192.168.10.11/32 encap seg6 mode encap segs 2001:db8:1001:1::11 dev lf2-sp1"
ns lf2 "ip route replace 192.168.10.12/32 encap seg6 mode encap segs 2001:db8:1001:1::12 dev lf2-sp2"

# h4: plain steered route via sp2 (service detour kept only as an encoding example)
ns lf1 "ip route replace 192.168.11.14/32 encap seg6 mode encap segs 2001:db8:1002:1::14 dev lf1-sp2"

echo "Bidirectional SRv6 steering configured."
