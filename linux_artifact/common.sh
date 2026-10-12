#!/usr/bin/env bash
set -euo pipefail

SPINES=(sp1 sp2)
LEAFS=(lf1 lf2)
HOSTS=(h1 h2 h3 h4)
SERVICES=(svc1)
ALL_NS=("${SPINES[@]}" "${LEAFS[@]}" "${HOSTS[@]}" "${SERVICES[@]}")

log() {
  echo "[$(date +%H:%M:%S)] $*"
}

run() {
  echo "+ $*"
  eval "$@"
}

ns() {
  local n="$1"
  shift
  run "ip netns exec ${n} $*"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Please run as root."
    exit 1
  fi
}

enable_forwarding() {
  local n="$1"
  ns "$n" "sysctl -w net.ipv4.ip_forward=1 >/dev/null"
  ns "$n" "sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null"
}

enable_srv6() {
  local n="$1"
  ns "$n" "sysctl -w net.ipv6.conf.all.seg6_enabled=1 >/dev/null || true"
  ns "$n" "sysctl -w net.ipv6.conf.default.seg6_enabled=1 >/dev/null || true"
  ns "$n" "sysctl -w net.ipv6.conf.lo.seg6_enabled=1 >/dev/null || true"
}
