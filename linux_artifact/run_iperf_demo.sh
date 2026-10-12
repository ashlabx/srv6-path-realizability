#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

# Start one-off iperf3 server on h3
ns h3 "pkill -f iperf3 || true"
ns h3 "iperf3 -s -D"
sleep 1

echo "== iperf3 from h1 to h3 =="
ns h1 "iperf3 -c 192.168.11.13 -t 5"

ns h3 "pkill -f iperf3 || true"
