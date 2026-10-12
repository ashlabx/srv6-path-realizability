#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

echo "== Underlay reachability =="
ns lf1 "ping -c 2 10.255.2.1"
ns lf2 "ping -c 2 10.255.1.1"

echo "== Host reachability over VXLAN =="
ns h1 "ping -c 3 192.168.11.13"
ns h2 "ping -c 3 192.168.11.14"

echo "== VXLAN devices =="
ns lf1 "ip -d link show vxlan10010"
ns lf2 "ip -d link show vxlan10010"

echo "VXLAN validation complete."
