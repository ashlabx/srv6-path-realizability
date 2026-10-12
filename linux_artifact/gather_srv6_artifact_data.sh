#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

OUTDIR="artifact_outputs"
mkdir -p "${OUTDIR}"

echo "[1/8] Locator reachability logs"
ns lf1 "ping6 -I 2001:db8:1001::1 -c 2 2001:db8:1002::1" | tee "${OUTDIR}/lf1_to_lf2_locator_ping.txt"
ns lf2 "ping6 -I 2001:db8:1002::1 -c 2 2001:db8:1001::1" | tee "${OUTDIR}/lf2_to_lf1_locator_ping.txt"

echo "[2/8] Full IPv6 routing tables"
ns lf1 "ip -6 route" > "${OUTDIR}/lf1_srv6_routes.txt"
ns lf2 "ip -6 route" > "${OUTDIR}/lf2_srv6_routes.txt"
ns sp1 "ip -6 route" > "${OUTDIR}/sp1_srv6_routes.txt"
ns sp2 "ip -6 route" > "${OUTDIR}/sp2_srv6_routes.txt"

echo "[3/8] Focused seg6 route state"
ns lf1 "ip route show | grep seg6 || true" > "${OUTDIR}/lf1_seg6_routes.txt"
ns lf2 "ip -6 route show | grep 2001:db8:1002:1:: || true" > "${OUTDIR}/lf2_sid_routes.txt"

echo "[4/8] Loopback/locator state"
ns lf1 "ip addr show lo" > "${OUTDIR}/lf1_lo.txt"
ns lf2 "ip addr show lo" > "${OUTDIR}/lf2_lo.txt"

echo "[5/8] Route resolution"
ns lf1 "ip -6 route get 2001:db8:1002::1" > "${OUTDIR}/lf1_route_get_remote_locator.txt"
ns lf2 "ip -6 route get 2001:db8:1001::1" > "${OUTDIR}/lf2_route_get_remote_locator.txt"

echo "[6/8] Optional host reachability logs"
ns h1 "ping -c 3 192.168.11.13 || true" | tee "${OUTDIR}/h1_to_h3_ping.txt"
ns h2 "ping -c 3 192.168.11.14 || true" | tee "${OUTDIR}/h2_to_h4_ping.txt"

echo "[7/8] Optional tcpdump transcript for locator ping"
if command -v tcpdump >/dev/null 2>&1; then
  (
    ip netns exec lf1 tcpdump -ni any -c 6 ip6 > "${OUTDIR}/lf1_tcpdump_locator.txt" 2>&1 &
    TCPDUMP_PID=$!
    sleep 1
    ip netns exec lf1 ping6 -I 2001:db8:1001::1 -c 2 2001:db8:1002::1 >/dev/null 2>&1 || true
    wait ${TCPDUMP_PID} || true
  )
else
  echo "tcpdump not installed" > "${OUTDIR}/lf1_tcpdump_locator.txt"
fi

echo "[8/8] Optional tcpdump transcript for SRv6 host-path attempt"
if command -v tcpdump >/dev/null 2>&1; then
  (
    ip netns exec lf1 tcpdump -ni any -c 6 ip6 > "${OUTDIR}/lf1_tcpdump_hostpath.txt" 2>&1 &
    TCPDUMP_PID=$!
    sleep 1
    ip netns exec h1 ping -c 2 192.168.11.13 >/dev/null 2>&1 || true
    wait ${TCPDUMP_PID} || true
  )
else
  echo "tcpdump not installed" > "${OUTDIR}/lf1_tcpdump_hostpath.txt"
fi

echo "Artifact data gathered in ${OUTDIR}/"
