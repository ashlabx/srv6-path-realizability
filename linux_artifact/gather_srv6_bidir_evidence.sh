#!/usr/bin/env bash
# Collects the evidence that the revised Section 6 would cite once rerun:
# host-to-host reachability over SRv6 and SRH-bearing packets observed on BOTH
# the lf1 uplink (egress) and the lf2 uplink (arrival at the remote leaf).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root
OUT=artifact_outputs_bidir; mkdir -p "$OUT"
ip netns exec lf2 tcpdump -ni any -c 8 'ip6 and ip6[6]==43' > "$OUT/lf2_tcpdump_srh_arrival.txt" 2>&1 &
P2=$!
ip netns exec lf1 tcpdump -ni any -c 8 'ip6 and ip6[6]==43' > "$OUT/lf1_tcpdump_srh_egress.txt" 2>&1 &
P1=$!
sleep 1
ns h1 "ping -c 4 192.168.11.13" | tee "$OUT/h1_to_h3_ping.txt" || true
ns h2 "ping -c 4 192.168.11.14" | tee "$OUT/h2_to_h4_ping.txt" || true
wait $P1 $P2 || true
ns lf1 "ip route show | grep seg6" > "$OUT/lf1_seg6_routes.txt" || true
ns lf2 "ip route show | grep seg6" > "$OUT/lf2_seg6_routes.txt" || true
ns lf1 "ip -6 route show | grep seg6local" > "$OUT/lf1_sids.txt" || true
ns lf2 "ip -6 route show | grep seg6local" > "$OUT/lf2_sids.txt" || true
echo "Evidence written to $OUT/"
