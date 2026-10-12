#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

CAPDIR="${1:-/tmp/linux_realizability_caps}"
mkdir -p "${CAPDIR}"

# Example captures to verify service/path realization
ns lf1 "timeout 12 tcpdump -ni any -w ${CAPDIR}/lf1.pcap icmp or udp port 4789 or ip6" &
P1=$!
ns lf2 "timeout 12 tcpdump -ni any -w ${CAPDIR}/lf2.pcap icmp or udp port 4789 or ip6" &
P2=$!
ns svc1 "timeout 12 tcpdump -ni any -w ${CAPDIR}/svc1.pcap icmp or ip" &
P3=$!

sleep 2
ns h1 "ping -c 3 192.168.11.14" || true

wait $P1 || true
wait $P2 || true
wait $P3 || true

echo "Captures saved in ${CAPDIR}"
