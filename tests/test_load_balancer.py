"""
tests/test_load_balancer.py
----------------------------
Unit tests for core load balancer logic.

Run:
    pytest tests/ -v
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.load_balancer import (
    LoadBalancer,
    generateRandomIP,
    set_node_health,
    get_health_status,
    get_metrics,
    reset_metrics,
    NODES,
    _hrw_score,
)


# ─────────────────────────────────────────────
#  Setup / Teardown
# ─────────────────────────────────────────────
@pytest.fixture(autouse=True)
def reset_before_each():
    """Reset metrics and restore all nodes to healthy before every test."""
    reset_metrics()
    for node in NODES:
        node["healthy"] = True
    yield


# ─────────────────────────────────────────────
#  Test: IP Generator
# ─────────────────────────────────────────────
def test_generateRandomIP_format():
    ip = generateRandomIP()
    parts = ip.split(".")
    assert len(parts) == 4
    assert all(0 <= int(p) <= 255 for p in parts)


def test_generateRandomIP_unique():
    ips = {generateRandomIP() for _ in range(20)}
    assert len(ips) > 1  # very unlikely all 20 are the same


# ─────────────────────────────────────────────
#  Test: Determinism (R1 — same IP → same node)
# ─────────────────────────────────────────────
def test_same_ip_always_same_node():
    # Use a fresh IP each test run and only call 5 times (within rate limit)
    ip = "10.20.30.40"
    results = {LoadBalancer(ip)["node"] for _ in range(5)}
    assert len(results) == 1, "Same IP must always route to the same node"


def test_different_ips_can_hit_different_nodes():
    nodes_hit = {LoadBalancer(generateRandomIP())["node"] for _ in range(50)}
    assert len(nodes_hit) > 1, "Different IPs should distribute across nodes"


# ─────────────────────────────────────────────
#  Test: Stability on node changes (R2)
# ─────────────────────────────────────────────
def test_stable_on_node_removal():
    """
    IPs not assigned to the removed node should keep their assignment.
    This is the key advantage of Rendezvous over modulo hashing.
    """
    test_ips = [f"192.168.1.{i}" for i in range(1, 50)]

    # Record initial assignments
    initial = {ip: LoadBalancer(ip)["node"] for ip in test_ips}

    # Take Node-A offline
    set_node_health("Node-A", False)

    # Re-route
    after_removal = {ip: LoadBalancer(ip)["node"] for ip in test_ips}

    # IPs that weren't on Node-A must keep their assignment
    for ip in test_ips:
        if initial[ip] != "Node-A":
            assert after_removal[ip] == initial[ip], (
                f"{ip} was on {initial[ip]} and should not have moved"
            )


# ─────────────────────────────────────────────
#  Test: Health checks
# ─────────────────────────────────────────────
def test_unhealthy_node_not_selected():
    set_node_health("Node-A", False)
    set_node_health("Node-B", False)
    for _ in range(20):
        result = LoadBalancer(generateRandomIP())
        assert result["node"] == "Node-C"


def test_all_nodes_down_raises():
    for node in NODES:
        node["healthy"] = False
    with pytest.raises(RuntimeError, match="All nodes are down"):
        LoadBalancer("1.2.3.4")


def test_health_status_reflects_changes():
    set_node_health("Node-B", False)
    status = {n["name"]: n["healthy"] for n in get_health_status()}
    assert status["Node-A"] is True
    assert status["Node-B"] is False
    assert status["Node-C"] is True


# ─────────────────────────────────────────────
#  Test: Rate Limiting
# ─────────────────────────────────────────────
def test_rate_limit_triggers():
    ip = "99.99.99.99"
    results = [LoadBalancer(ip) for _ in range(10)]
    statuses = [r["status"] for r in results]
    assert "rate_limited" in statuses


def test_rate_limit_allows_up_to_limit():
    ip = "88.88.88.88"
    results = [LoadBalancer(ip) for _ in range(5)]
    assert all(r["status"] == "routed" for r in results)


# ─────────────────────────────────────────────
#  Test: Metrics
# ─────────────────────────────────────────────
def test_metrics_count_requests():
    for _ in range(15):
        LoadBalancer(generateRandomIP())
    m = get_metrics()
    assert m["total_requests"] == 15


def test_metrics_reset():
    for _ in range(5):
        LoadBalancer(generateRandomIP())
    reset_metrics()
    m = get_metrics()
    assert m["total_requests"] == 0


# ─────────────────────────────────────────────
#  Test: HRW score determinism
# ─────────────────────────────────────────────
def test_hrw_score_deterministic():
    s1 = _hrw_score("10.0.0.1", "Node-A", 3)
    s2 = _hrw_score("10.0.0.1", "Node-A", 3)
    assert s1 == s2


def test_hrw_weight_effect():
    """Higher weight should produce a proportionally higher score."""
    base = _hrw_score("1.2.3.4", "Node-X", 1)
    weighted = _hrw_score("1.2.3.4", "Node-X", 5)
    assert weighted == 5 * base
