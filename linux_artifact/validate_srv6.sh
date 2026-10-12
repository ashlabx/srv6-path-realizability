#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

echo "== Underlay IPv6 reachability =="
ns lf1 "ping6 -c 2 2001:db8:1002::1"
ns lf2 "ping6 -c 2 2001:db8:1001::1"

echo "== Host reachability over SRv6 steering =="
ns h1 "ping -c 3 192.168.11.13"
ns h2 "ping -c 3 192.168.11.14"

echo "== Local SID entries =="
ns lf2 "ip -6 route show | grep 2001:db8:1002:1:: || true"
ns lf1 "ip -6 route show | grep 2001:db8:1001:10::1 || true"

echo "== Encapsulating routes at lf1 =="
ns lf1 "ip route show | grep seg6 || true"

echo "SRv6 validation complete."
