#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

OUTDIR="artifact_outputs"
mkdir -p "${OUTDIR}"

echo "[1/8] VTEP reachability logs"
ns lf1 "ping -I 10.255.1.1 -c 2 10.255.2.1" | tee "${OUTDIR}/lf1_to_lf2_vtep_ping.txt"
ns lf2 "ping -I 10.255.2.1 -c 2 10.255.1.1" | tee "${OUTDIR}/lf2_to_lf1_vtep_ping.txt"

echo "[2/8] VXLAN device state"
ns lf1 "ip -d link show vxlan10010" > "${OUTDIR}/lf1_vxlan_state.txt"
ns lf2 "ip -d link show vxlan10010" > "${OUTDIR}/lf2_vxlan_state.txt"

echo "[3/8] IPv4 routing tables"
ns lf1 "ip route" > "${OUTDIR}/lf1_routes.txt"
ns lf2 "ip route" > "${OUTDIR}/lf2_routes.txt"
ns sp1 "ip route" > "${OUTDIR}/sp1_routes.txt"
ns sp2 "ip route" > "${OUTDIR}/sp2_routes.txt"

echo "[4/8] Bridge membership"
ns lf1 "bridge link" > "${OUTDIR}/lf1_bridge_link.txt"
ns lf2 "bridge link" > "${OUTDIR}/lf2_bridge_link.txt"

echo "[5/8] Bridge forwarding database"
ns lf1 "bridge fdb show" > "${OUTDIR}/lf1_fdb.txt"
ns lf2 "bridge fdb show" > "${OUTDIR}/lf2_fdb.txt"

echo "[6/8] Loopback/VTEP addresses"
ns lf1 "ip addr show lo" > "${OUTDIR}/lf1_lo.txt"
ns lf2 "ip addr show lo" > "${OUTDIR}/lf2_lo.txt"

echo "[7/8] Focused route resolution"
ns lf1 "ip route get 10.255.2.1" > "${OUTDIR}/lf1_route_get_remote_vtep.txt"
ns lf2 "ip route get 10.255.1.1" > "${OUTDIR}/lf2_route_get_remote_vtep.txt"

echo "[8/8] Optional tcpdump transcript"
if command -v tcpdump >/dev/null 2>&1; then
  (
    ip netns exec lf1 tcpdump -ni any -c 6 udp port 4789 > "${OUTDIR}/lf1_tcpdump_vxlan.txt" 2>&1 &
    TCPDUMP_PID=$!
    sleep 1
    ip netns exec lf1 ping -I 10.255.1.1 -c 2 10.255.2.1 >/dev/null 2>&1 || true
    wait ${TCPDUMP_PID} || true
  )
else
  echo "tcpdump not installed" > "${OUTDIR}/lf1_tcpdump_vxlan.txt"
fi

echo "Artifact data gathered in ${OUTDIR}/"
