#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

echo "== Ping matrix =="
ns h1 "ping -c 5 192.168.11.13"
ns h1 "ping -c 5 192.168.11.14"
ns h2 "ping -c 5 192.168.11.13"
ns h2 "ping -c 5 192.168.11.14"
