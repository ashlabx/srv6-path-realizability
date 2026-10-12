#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

for nsn in "${ALL_NS[@]}"; do
  ip netns del "${nsn}" 2>/dev/null || true
done

# Delete any stray veths that might remain if a previous run half-failed.
for dev in lf1-sp1 lf1-sp2 lf2-sp1 lf2-sp2 sp1-lf1 sp2-lf1 sp1-lf2 sp2-lf2 \
           lf1-h1 lf1-h2 lf2-h3 lf2-h4 h1-lf1 h2-lf1 h3-lf2 h4-lf2 \
           lf1-svc1 svc1-lf1; do
  ip link del "${dev}" 2>/dev/null || true
done

echo "Cleanup complete."
