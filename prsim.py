#!/usr/bin/env python3
"""
prsim: flow-level discrete-event simulator for the path-realizability study
"Path Realizability Under Contention: SRv6 as a Programmable Virtualization
Substrate for AI-Scale Infrastructure" (IJECE, paper ID 42851, revision 1).

Model summary (see README.md and config.json for every parameter)
-----------------------------------------------------------------
* Fabric: L leaves x S spines Clos, H hosts per leaf. Every directed link
  (host->leaf, leaf->spine, spine->leaf, leaf->host) is a FIFO,
  non-preemptive, work-conserving server with capacity C (bit/s).
* Flow-level serial service with cut-through: a flow of W wire-bytes
  occupies a link for W*8/C seconds. Its head reaches link k at time a_k;
  service starts at s_k = max(a_k, free_k); service ends at
  f_k = max(s_k + W*8/C_k, f_{k-1} + d_prop); free_k := f_k; the head is
  forwarded to link k+1 at s_k + d_prop. Heads are processed in global
  time order (event heap), so each link serves flows FIFO by head arrival.
* Queueing delay of a flow = sum_k (s_k - a_k). FCT = f_last - release.
* Wire bytes: W = B * (P + h) / P, where B is payload bytes, P the payload
  per packet (MTU payload) and h the per-packet encapsulation header:
     VXLAN over IPv4 : h = 50 B  (outer Eth 14 + IPv4 20 + UDP 8 + VXLAN 8)
     SRv6 (H.Encaps) : h = 14 + 40 + 8 + 16*n B  (outer Eth + IPv6 + SRH)
  Header overhead is modelled ONLY as serialization expansion; no
  per-segment processing cost is modelled (set seg_proc_ns to add one).
* Path choice happens once per flow at its release time and only concerns
  the spine (the single multipath decision in a 2-tier Clos).

Forwarding models (the four-way ablation)
-----------------------------------------
Every steered model uses the SAME controller: at release time it chooses
the intended spine sigma* = argmin_s max(free[src_leaf->s], free[s->dst_leaf])
+ serialization, i.e. it sees the same link-state snapshot for every
substrate. The substrates differ ONLY in how the intended spine is realised:

  vxlan_ecmp      no intent; spine = hash(outer 5-tuple)  (uniform per flow)
  srv6_ecmp       no intent; spine = hash(IPv6 flow label) (uniform per flow)
  vxlan_steer     intent realised through outer-UDP-source-port entropy.
                  With probability phi the chosen port lands on the intended
                  spine; otherwise the flow falls to the underlay hash.
                  phi = 1 is the idealised case (controller knows and controls
                  the hash exactly, per flow).
  vxlan_steer_tun intent realised by underlay policy on the remote-VTEP
                  prefix: one spine per (src leaf, dst leaf) tunnel, chosen
                  by the same controller for the first flow of the tunnel in
                  each epoch and reused for all later flows of that tunnel in
                  the epoch (tunnel-granular realisation).
  srv6_steer      intent encoded as an explicit SID list; realised exactly.

Path realizability R = fraction of steered flows whose realised spine
equals the controller's intended spine.
"""
import argparse, heapq, json, math, os, sys
import numpy as np

# --------------------------------------------------------------------------
# Topology
# --------------------------------------------------------------------------
class Fabric:
    def __init__(self, n_leaf, n_spine, hosts_per_leaf, c_host, c_fabric,
                 spine_scale=None):
        self.L, self.S, self.H = n_leaf, n_spine, hosts_per_leaf
        self.n_hosts = n_leaf * hosts_per_leaf
        self.links = {}  # name -> capacity (bit/s)
        for h in range(self.n_hosts):
            self.links[("h2l", h)] = c_host
            self.links[("l2h", h)] = c_host
        for l in range(n_leaf):
            for s in range(n_spine):
                sc = 1.0 if spine_scale is None else spine_scale.get((l, s), 1.0)
                self.links[("l2s", l, s)] = c_fabric * sc
                self.links[("s2l", s, l)] = c_fabric * sc
        self.idx = {k: i for i, k in enumerate(self.links)}
        self.cap = np.array([self.links[k] for k in self.links])

    def leaf_of(self, h):
        return h // self.H

    def path(self, src, dst, spine):
        ls, ld = self.leaf_of(src), self.leaf_of(dst)
        if ls == ld:
            return [self.idx[("h2l", src)], self.idx[("l2h", dst)]]
        return [self.idx[("h2l", src)], self.idx[("l2s", ls, spine)],
                self.idx[("s2l", spine, ld)], self.idx[("l2h", dst)]]

# --------------------------------------------------------------------------
# Workloads  (all sizes in bytes, times in seconds)
# --------------------------------------------------------------------------
def remote_hosts(fab, h):
    return [d for d in range(fab.n_hosts) if fab.leaf_of(d) != fab.leaf_of(h)]

def wl_all_to_all(fab, rng, p):
    flows = []
    for r in range(p["rounds"]):
        t0 = r * p["round_gap_ms"] * 1e-3
        for h in range(fab.n_hosts):
            dsts = remote_hosts(fab, h)
            rng.shuffle(dsts)
            for d in dsts:
                flows.append((t0 + rng.uniform(0, p["jitter_us"] * 1e-6),
                              h, d, p["msg_bytes"], r))
    return flows

def wl_incast(fab, rng, p):
    flows, t = [], 0.0
    for e in range(p["events"]):
        t += rng.exponential(p["mean_interarrival_ms"] * 1e-3)
        rcv = int(rng.integers(fab.n_hosts))
        cands = remote_hosts(fab, rcv)
        snd = rng.choice(cands, size=p["fan_in"], replace=False)
        for s in snd:
            flows.append((t + rng.uniform(0, p["jitter_us"] * 1e-6),
                          int(s), rcv, p["msg_bytes"], e))
    return flows

def wl_bursty(fab, rng, p):
    flows, t = [], 0.0
    for b in range(p["bursts"]):
        t += rng.exponential(p["mean_interarrival_ms"] * 1e-3)
        snd = rng.choice(fab.n_hosts, size=p["senders"], replace=False)
        for s in snd:
            cands = remote_hosts(fab, int(s))
            rcv = rng.choice(cands, size=p["receivers"], replace=False)
            for d in rcv:
                size = min(p["max_bytes"],
                           rng.lognormal(math.log(p["median_bytes"]), p["sigma"]))
                flows.append((t + rng.uniform(0, p["jitter_us"] * 1e-6),
                              int(s), int(d), float(size), b))
    return flows

WORKLOADS = {"all_to_all": wl_all_to_all, "incast": wl_incast,
             "bursty": wl_bursty}

# --------------------------------------------------------------------------
# Encapsulation overhead
# --------------------------------------------------------------------------
def header_bytes(substrate, segs):
    if substrate == "vxlan":
        return 50
    return 14 + 40 + 8 + 16 * segs      # outer Eth + IPv6 + SRH(8 + 16n)

def wire_factor(substrate, segs, payload):
    return (payload + header_bytes(substrate, segs)) / payload

# --------------------------------------------------------------------------
# Simulation core
# --------------------------------------------------------------------------
def simulate(fab, flows, model, rng, cfg, segs=1, phi=1.0, trace=None):
    substrate = "srv6" if model.startswith("srv6") else "vxlan"
    wf = wire_factor(substrate, segs, cfg["payload_bytes"])
    prop = cfg["prop_us"] * 1e-6
    seg_proc = cfg.get("seg_proc_ns", 0.0) * 1e-9 * (segs if substrate == "srv6" else 0)
    free = np.zeros(len(fab.cap))
    load_bytes = np.zeros(len(fab.cap))
    n = len(flows)
    order = sorted(range(n), key=lambda i: flows[i][0])
    # per-flow state
    path = [None] * n
    intended = np.full(n, -1)
    realised = np.full(n, -1)
    wbytes = np.zeros(n)
    qdelay = np.zeros(n)
    finish_prev = np.zeros(n)
    fct = np.zeros(n)
    tunnel_pin = {}  # (ls, ld, epoch) -> spine
    # event heap entries: (time, seq, flow, hop). Flow releases are inserted
    # lazily so that the controller sees link state at the release instant.
    heap, seq = [], 0
    for i in order:
        heapq.heappush(heap, (flows[i][0], seq, i, -1)); seq += 1
    S = fab.S
    # common random numbers: the underlay hash outcome and the entropy-steering
    # draw of each flow are fixed per flow, identical across models
    hash_draw = rng.integers(S, size=n)
    # controller ledger: bytes the controller has placed on each fabric link
    # that have not yet been served there (its view of committed load)
    ledger = np.zeros(len(fab.cap))
    believed = [None] * n
    phi_draw = rng.random(n)
    while heap:
        t, _, i, hop = heapq.heappop(heap)
        rel, src, dst, B, epoch = flows[i]
        if hop == -1:  # release: routing decision
            ls, ld = fab.leaf_of(src), fab.leaf_of(dst)
            W = B * wf
            wbytes[i] = W
            sp = 0
            if ls != ld:
                h_choice = int(hash_draw[i])  # the underlay hash outcome
                if model in ("vxlan_ecmp", "srv6_ecmp"):
                    sp = h_choice
                else:
                    # common controller: same objective, same state snapshot
                    best, bestv = None, None
                    for k in range(S):
                        s = (int(hash_draw[i]) + k) % S   # tie-break by hash
                        up, dn = fab.idx[("l2s", ls, s)], fab.idx[("s2l", s, ld)]
                        v = max(max(free[up], t) + (ledger[up] + W) * 8 / fab.cap[up],
                                max(free[dn], t) + (ledger[dn] + W) * 8 / fab.cap[dn])
                        if bestv is None or v < bestv - 1e-15:
                            best, bestv = s, v
                    if trace is not None:
                        trace.setdefault("decisions", []).append((i, t, ls, ld, W, best, bestv, free.copy(), ledger.copy()))
                    bu, bd = fab.idx[("l2s", ls, best)], fab.idx[("s2l", best, ld)]
                    ledger[bu] += W; ledger[bd] += W
                    believed[i] = (bu, bd)
                    intended[i] = best
                    if model == "srv6_steer":
                        sp = best
                    elif model == "vxlan_steer":
                        sp = best if phi_draw[i] < phi else h_choice
                    elif model == "vxlan_steer_tun":
                        key = (ls, ld, epoch)
                        if key not in tunnel_pin:
                            tunnel_pin[key] = best
                        sp = tunnel_pin[key]
                    else:
                        raise ValueError(model)
                realised[i] = sp
            path[i] = fab.path(src, dst, sp)
            finish_prev[i] = rel
            heapq.heappush(heap, (rel, seq, i, 0)); seq += 1
            continue
        link = path[i][hop]
        W = wbytes[i]
        s_k = max(t, free[link])
        f_k = max(s_k + W * 8 / fab.cap[link], finish_prev[i] + (prop if hop else 0))
        free[link] = f_k
        load_bytes[link] += W
        if believed[i] is not None and hop in (1, 2):
            ledger[believed[i][hop - 1]] -= W
        qdelay[i] += s_k - t
        if trace is not None:
            trace.setdefault("hops", []).append((i, hop, link, t, s_k, f_k, W))
        finish_prev[i] = f_k
        if hop + 1 < len(path[i]):
            heapq.heappush(heap, (s_k + prop + seg_proc, seq, i, hop + 1)); seq += 1
        else:
            fct[i] = f_k - rel
    if trace is not None:
        trace.update(path=path, fct=fct.copy(), wbytes=wbytes.copy(), realised=realised.copy(),
                     intended=intended.copy(), wire_factor=wf, prop=prop)
    # metrics
    remote = realised >= 0
    steered = intended >= 0
    R = float(np.mean(realised[steered] == intended[steered])) if steered.any() else float("nan")
    imb = []
    for l in range(fab.L):
        up = np.array([load_bytes[fab.idx[("l2s", l, s)]] for s in range(S)])
        dn = np.array([load_bytes[fab.idx[("s2l", s, l)]] for s in range(S)])
        for v in (up, dn):
            if v.mean() > 0:
                imb.append((v.max() - v.min()) / v.mean())
    return {
        "p99_fct_ms": float(np.percentile(fct, 99) * 1e3),
        "p50_fct_ms": float(np.percentile(fct, 50) * 1e3),
        "mean_fct_ms": float(np.mean(fct) * 1e3),
        "mean_qdelay_ms": float(np.mean(qdelay) * 1e3),
        "p99_qdelay_ms": float(np.percentile(qdelay, 99) * 1e3),
        "spine_imbalance_pct": float(np.mean(imb) * 100) if imb else 0.0,
        "realizability": R,
        "n_flows": n,
    }

def build_fabric(cfg, load_pct=100.0, degraded=None):
    scale = 100.0 / load_pct   # effective load = C_nominal / C_effective
    t = cfg["topology"]
    sp_scale = None
    if degraded:
        sp_scale = {(degraded["leaf"], degraded["spine"]): degraded["factor"]}
    return Fabric(t["leaves"], t["spines"], t["hosts_per_leaf"],
                  t["host_gbps"] * 1e9 * scale, t["fabric_gbps"] * 1e9 * scale,
                  sp_scale)

def run_one(cfg, workload, model, seed, load_pct=100.0, segs=1, phi=None,
            degraded=None):
    fab = build_fabric(cfg, load_pct, degraded)
    wl_rng = np.random.default_rng([seed, 1])          # common random numbers:
    flows = WORKLOADS[workload](fab, wl_rng, cfg["workloads"][workload])
    route_rng = np.random.default_rng([seed, 2])       # same hash draws per model
    if phi is None:
        phi = cfg["vxlan_entropy_fidelity"]
    return simulate(fab, flows, model, route_rng, cfg, segs=segs, phi=phi)

def offered_utilisation(cfg, workload, seed, load_pct=100.0):
    """Offered utilisation rho of the leaf->spine tier:
         rho = 8 * sum(inter-leaf payload bytes) / (T * sum_l,s C_ls,eff)
    with T = rounds * round_gap for all-to-all and T = last release time for
    the Poisson workloads. rho scales linearly with the effective load."""
    fab = build_fabric(cfg, load_pct)
    p = cfg["workloads"][workload]
    fl = WORKLOADS[workload](fab, np.random.default_rng([seed, 1]), p)
    B = sum(f[3] for f in fl if fab.leaf_of(f[1]) != fab.leaf_of(f[2]))
    T = p["rounds"] * p["round_gap_ms"] * 1e-3 if workload == "all_to_all" else max(f[0] for f in fl)
    cap = sum(fab.links[k] for k in fab.links if k[0] == "l2s")
    return 8 * B / (T * cap)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "config.json"))
    ap.add_argument("--workload", default="all_to_all")
    ap.add_argument("--model", default="srv6_steer")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--load", type=float, default=100.0)
    ap.add_argument("--segs", type=int, default=1)
    ap.add_argument("--phi", type=float, default=None)
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    print(json.dumps(run_one(cfg, a.workload, a.model, a.seed, a.load, a.segs, a.phi), indent=2))
