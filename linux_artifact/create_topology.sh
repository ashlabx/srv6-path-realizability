#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_root

# Namespaces
for nsn in "${ALL_NS[@]}"; do
  ip netns add "${nsn}"
  ns "${nsn}" "ip link set lo up"
done

# Leaf-spine links
ip link add lf1-sp1 type veth peer name sp1-lf1
ip link add lf1-sp2 type veth peer name sp2-lf1
ip link add lf2-sp1 type veth peer name sp1-lf2
ip link add lf2-sp2 type veth peer name sp2-lf2

ip link set lf1-sp1 netns lf1
ip link set sp1-lf1 netns sp1
ip link set lf1-sp2 netns lf1
ip link set sp2-lf1 netns sp2
ip link set lf2-sp1 netns lf2
ip link set sp1-lf2 netns sp1
ip link set lf2-sp2 netns lf2
ip link set sp2-lf2 netns sp2

# Host links
ip link add lf1-h1 type veth peer name h1-lf1
ip link add lf1-h2 type veth peer name h2-lf1
ip link add lf2-h3 type veth peer name h3-lf2
ip link add lf2-h4 type veth peer name h4-lf2

ip link set lf1-h1 netns lf1
ip link set h1-lf1 netns h1
ip link set lf1-h2 netns lf1
ip link set h2-lf1 netns h2
ip link set lf2-h3 netns lf2
ip link set h3-lf2 netns h3
ip link set lf2-h4 netns lf2
ip link set h4-lf2 netns h4

# Service link attached to lf1
ip link add lf1-svc1 type veth peer name svc1-lf1
ip link set lf1-svc1 netns lf1
ip link set svc1-lf1 netns svc1

# Bring up interfaces
for i in lf1-sp1 lf1-sp2 lf1-h1 lf1-h2 lf1-svc1; do ns lf1 "ip link set ${i} up"; done
for i in lf2-sp1 lf2-sp2 lf2-h3 lf2-h4; do ns lf2 "ip link set ${i} up"; done
for i in sp1-lf1 sp1-lf2; do ns sp1 "ip link set ${i} up"; done
for i in sp2-lf1 sp2-lf2; do ns sp2 "ip link set ${i} up"; done
ns h1 "ip link set h1-lf1 up"
ns h2 "ip link set h2-lf1 up"
ns h3 "ip link set h3-lf2 up"
ns h4 "ip link set h4-lf2 up"
ns svc1 "ip link set svc1-lf1 up"

# IPv4 underlay
ns lf1 "ip addr add 10.0.11.1/30 dev lf1-sp1"
ns sp1 "ip addr add 10.0.11.2/30 dev sp1-lf1"
ns lf1 "ip addr add 10.0.12.1/30 dev lf1-sp2"
ns sp2 "ip addr add 10.0.12.2/30 dev sp2-lf1"

ns lf2 "ip addr add 10.0.21.1/30 dev lf2-sp1"
ns sp1 "ip addr add 10.0.21.2/30 dev sp1-lf2"
ns lf2 "ip addr add 10.0.22.1/30 dev lf2-sp2"
ns sp2 "ip addr add 10.0.22.2/30 dev sp2-lf2"

# IPv6 underlay
ns lf1 "ip -6 addr add 2001:db8:11::1/64 dev lf1-sp1"
ns sp1 "ip -6 addr add 2001:db8:11::2/64 dev sp1-lf1"
ns lf1 "ip -6 addr add 2001:db8:12::1/64 dev lf1-sp2"
ns sp2 "ip -6 addr add 2001:db8:12::2/64 dev sp2-lf1"

ns lf2 "ip -6 addr add 2001:db8:21::1/64 dev lf2-sp1"
ns sp1 "ip -6 addr add 2001:db8:21::2/64 dev sp1-lf2"
ns lf2 "ip -6 addr add 2001:db8:22::1/64 dev lf2-sp2"
ns sp2 "ip -6 addr add 2001:db8:22::2/64 dev sp2-lf2"

# Routing-forwarding nodes
for n in lf1 lf2 sp1 sp2; do
  enable_forwarding "$n"
  enable_srv6 "$n"
done

# Simple spine routes to leaf loopbacks/locators will be installed by setup scripts.
echo "Topology created."
