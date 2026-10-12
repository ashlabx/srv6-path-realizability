#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

# Create local bridges for host-facing subnets
ns lf1 "ip link add brA type bridge"
ns lf1 "ip link set brA up"
ns lf1 "ip link set lf1-h1 master brA"
ns lf1 "ip link set lf1-h2 master brA"
ns lf1 "ip addr add 192.168.10.1/24 dev brA"

ns lf2 "ip link add brA type bridge"
ns lf2 "ip link set brA up"
ns lf2 "ip link set lf2-h3 master brA"
ns lf2 "ip link set lf2-h4 master brA"
ns lf2 "ip addr add 192.168.11.1/24 dev brA"

# Host IPs
ns h1 "ip addr add 192.168.10.11/24 dev h1-lf1"
ns h2 "ip addr add 192.168.10.12/24 dev h2-lf1"
ns h3 "ip addr add 192.168.11.13/24 dev h3-lf2"
ns h4 "ip addr add 192.168.11.14/24 dev h4-lf2"
ns h1 "ip route add default via 192.168.10.1"
ns h2 "ip route add default via 192.168.10.1"
ns h3 "ip route add default via 192.168.11.1"
ns h4 "ip route add default via 192.168.11.1"

# SRv6 locators
ns lf1 "ip -6 addr add 2001:db8:1001::1/48 dev lo || true"
ns lf2 "ip -6 addr add 2001:db8:1002::1/48 dev lo || true"

# Basic locator reachability via both spines
ns lf1 "ip -6 route add 2001:db8:1002::/48 nexthop via 2001:db8:11::2 dev lf1-sp1 nexthop via 2001:db8:12::2 dev lf1-sp2 || true"
ns lf2 "ip -6 route add 2001:db8:1001::/48 nexthop via 2001:db8:21::2 dev lf2-sp1 nexthop via 2001:db8:22::2 dev lf2-sp2 || true"
ns sp1 "ip -6 route add 2001:db8:1001::/48 via 2001:db8:11::1 dev sp1-lf1 || true"
ns sp1 "ip -6 route add 2001:db8:1002::/48 via 2001:db8:21::1 dev sp1-lf2 || true"
ns sp2 "ip -6 route add 2001:db8:1001::/48 via 2001:db8:12::1 dev sp2-lf1 || true"
ns sp2 "ip -6 route add 2001:db8:1002::/48 via 2001:db8:22::1 dev sp2-lf2 || true"

# Local SIDs:
#   lf2 delivery SID for 192.168.11.13 (h3)
#   lf2 delivery SID for 192.168.11.14 (h4)
#   lf1 service SID forwarding into svc1
ns svc1 "ip addr add 172.16.1.10/24 dev svc1-lf1 || true"
ns lf1 "ip addr add 172.16.1.1/24 dev lf1-svc1 || true"
ns svc1 "sysctl -w net.ipv4.ip_forward=1 >/dev/null"

ns lf2 "ip -6 route add 2001:db8:1002:1::13/128 encap seg6local action End.DX4 nh4 192.168.11.13 dev lo || true"
ns lf2 "ip -6 route add 2001:db8:1002:1::14/128 encap seg6local action End.DX4 nh4 192.168.11.14 dev lo || true"
ns lf1 "ip -6 route add 2001:db8:1001:10::1/128 encap seg6local action End.DX4 nh4 172.16.1.10 dev lo || true"

# Plain steered routes from lf1 to hosts on lf2
ns lf1 "ip route add 192.168.11.13/32 encap seg6 mode encap segs 2001:db8:1002:1::13 dev lf1-sp1 || true"
ns lf1 "ip route add 192.168.11.14/32 encap seg6 mode encap segs 2001:db8:1002:1::14 dev lf1-sp2 || true"

# Optional service-path example:
# h1/h2 traffic destined to h4 can be forced via service SID first.
ns lf1 "ip route replace 192.168.11.14/32 encap seg6 mode encap segs 2001:db8:1001:10::1,2001:db8:1002:1::14 dev lf1-sp1 || true"

echo "SRv6 steering baseline configured."
