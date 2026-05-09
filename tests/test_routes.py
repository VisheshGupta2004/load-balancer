"""
tests/test_routes.py
---------------------
Integration tests for Flask API endpoints.

Run:
    pytest tests/ -v
"""

import pytest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.load_balancer import reset_metrics, NODES


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        reset_metrics()
        for node in NODES:
            node["healthy"] = True
        yield c


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"Rendezvous" in r.data


def test_route_random_ip(client):
    r = client.post("/route", json={})
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "routed"
    assert "node" in data


def test_route_specific_ip(client):
    r = client.post("/route", json={"ip": "10.0.0.1"})
    assert r.status_code == 200
    assert r.get_json()["ip"] == "10.0.0.1"


def test_route_determinism(client):
    r1 = client.post("/route", json={"ip": "55.66.77.88"}).get_json()
    r2 = client.post("/route", json={"ip": "55.66.77.88"}).get_json()
    assert r1["node"] == r2["node"]


def test_simulate(client):
    r = client.post("/simulate", json={"count": 10})
    assert r.status_code == 200
    data = r.get_json()
    assert data["simulated"] == 10


def test_metrics(client):
    client.post("/simulate", json={"count": 5})
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total_requests"] == 5


def test_metrics_reset(client):
    client.post("/simulate", json={"count": 5})
    client.delete("/metrics/reset")
    r = client.get("/metrics")
    assert r.get_json()["total_requests"] == 0


def test_health_get(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert "nodes" in r.get_json()


def test_health_patch(client):
    r = client.patch("/health/Node-A", json={"healthy": False})
    assert r.status_code == 200
    assert r.get_json()["healthy"] is False


def test_health_patch_unknown_node(client):
    r = client.patch("/health/Node-Z", json={"healthy": False})
    assert r.status_code == 404


def test_nodes_list(client):
    r = client.get("/nodes")
    assert r.status_code == 200
    nodes = r.get_json()["nodes"]
    assert len(nodes) == 3
