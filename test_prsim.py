"""Sanity tests for prsim (run: python3 -m pytest -q test_prsim.py)."""
import json, os, numpy as np
import prsim

CFG = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))

def fab():
    return prsim.Fabric(4, 2, 4, 100e9, 100e9)

def test_single_flow_fct_is_serialization_plus_propagation():
    f = fab(); B = 1_000_000
    r = prsim.simulate(f, [(0.0, 0, 4, B, 0)], "srv6_steer", np.random.default_rng(0), CFG)
    W = B * prsim.wire_factor("srv6", 1, CFG["payload_bytes"])
    expect = W * 8 / 100e9 + 3 * CFG["prop_us"] * 1e-6     # cut-through, 4 hops
    assert abs(r["p99_fct_ms"] * 1e-3 - expect) < 1e-9
    assert r["mean_qdelay_ms"] == 0

def test_two_flows_share_nic_fifo():
    f = fab(); B = 1_000_000
    flows = [(0.0, 0, 4, B, 0), (0.0, 0, 8, B, 0)]
    r = prsim.simulate(f, flows, "vxlan_ecmp", np.random.default_rng(0), CFG)
    W = B * prsim.wire_factor("vxlan", 1, CFG["payload_bytes"])
    assert abs(r["mean_qdelay_ms"] * 1e-3 - W * 8 / 100e9 / 2) < 1e-9

def test_srv6_steer_realizability_is_one_and_ecmp_models_match_hash():
    r = prsim.run_one(CFG, "bursty", "srv6_steer", 3)
    assert r["realizability"] == 1.0
    a = prsim.run_one(CFG, "bursty", "vxlan_ecmp", 3)
    b = prsim.run_one(CFG, "bursty", "srv6_ecmp", 3)
    assert abs(a["spine_imbalance_pct"] - b["spine_imbalance_pct"]) < 1e-9  # same hash draws

def test_phi_one_equals_srv6_up_to_header():
    a = prsim.run_one(CFG, "all_to_all", "vxlan_steer", 2, phi=1.0)
    b = prsim.run_one(CFG, "all_to_all", "srv6_steer", 2)
    assert a["realizability"] == 1.0
    assert abs(a["p99_fct_ms"] / b["p99_fct_ms"] - 1) < 0.02

def test_header_overheads():
    assert prsim.header_bytes("vxlan", 1) == 50
    assert prsim.header_bytes("srv6", 1) == 78
    assert prsim.header_bytes("srv6", 6) == 158
