#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

# VTEP loopbacks
ns lf1 "ip addr add 10.255.1.1/32 dev lo || true"
ns lf2 "ip addr add 10.255.2.1/32 dev lo || true"

# Underlay routes to remote VTEPs
ns lf1 "ip route add 10.255.2.1/32 nexthop via 10.0.11.2 nexthop via 10.0.12.2 || true"
ns lf2 "ip route add 10.255.1.1/32 nexthop via 10.0.21.2 nexthop via 10.0.22.2 || true"
ns sp1 "ip route add 10.255.1.1/32 via 10.0.11.1 || true"
ns sp1 "ip route add 10.255.2.1/32 via 10.0.21.1 || true"
ns sp2 "ip route add 10.255.1.1/32 via 10.0.12.1 || true"
ns sp2 "ip route add 10.255.2.1/32 via 10.0.22.1 || true"

# Local L2 bridges
ns lf1 "ip link add brTenant type bridge"
ns lf1 "ip link set brTenant up"
ns lf2 "ip link add brTenant type bridge"
ns lf2 "ip link set brTenant up"

# Attach host-facing ports
ns lf1 "ip link set lf1-h1 master brTenant"
ns lf1 "ip link set lf1-h2 master brTenant"
ns lf2 "ip link set lf2-h3 master brTenant"
ns lf2 "ip link set lf2-h4 master brTenant"

# Tenant gateway IPs
ns lf1 "ip addr add 192.168.10.1/24 dev brTenant"
ns lf2 "ip addr add 192.168.11.1/24 dev brTenant"

# Host IP config
ns h1 "ip addr add 192.168.10.11/24 dev h1-lf1"
ns h2 "ip addr add 192.168.10.12/24 dev h2-lf1"
ns h3 "ip addr add 192.168.11.13/24 dev h3-lf2"
ns h4 "ip addr add 192.168.11.14/24 dev h4-lf2"
ns h1 "ip route add default via 192.168.10.1"
ns h2 "ip route add default via 192.168.10.1"
ns h3 "ip route add default via 192.168.11.1"
ns h4 "ip route add default via 192.168.11.1"

# VXLAN interface using static flood entry
ns lf1 "ip link add vxlan10010 type vxlan id 10010 local 10.255.1.1 dstport 4789 nolearning"
ns lf2 "ip link add vxlan10010 type vxlan id 10010 local 10.255.2.1 dstport 4789 nolearning"
ns lf1 "ip link set vxlan10010 up"
ns lf2 "ip link set vxlan10010 up"
ns lf1 "bridge fdb append 00:00:00:00:00:00 dev vxlan10010 dst 10.255.2.1"
ns lf2 "bridge fdb append 00:00:00:00:00:00 dev vxlan10010 dst 10.255.1.1"
ns lf1 "ip link set vxlan10010 master brTenant"
ns lf2 "ip link set vxlan10010 master brTenant"

# Optional service namespace addressing for future experiments
ns lf1 "ip addr add 172.16.1.1/24 dev lf1-svc1 || true"
ns svc1 "ip addr add 172.16.1.10/24 dev svc1-lf1 || true"
ns svc1 "sysctl -w net.ipv4.ip_forward=1 >/dev/null"

echo "VXLAN baseline configured."
