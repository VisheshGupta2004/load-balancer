"""
routes.py
---------
Flask API endpoints for the Load Balancer service.
All state is in-memory (no database required).
"""

from flask import Blueprint, request, jsonify
from app.load_balancer import (
    LoadBalancer,
    generateRandomIP,
    simulateTraffic,
    get_metrics,
    get_health_status,
    set_node_health,
    reset_metrics,
    NODES,
    request_log,
)

api = Blueprint("api", __name__)


# ─────────────────────────────────────────────
#  POST /route
#  Route a specific IP through the load balancer
# ─────────────────────────────────────────────
@api.route("/route", methods=["POST"])
def route_request():
    """
    Route a given IP to a node.
    Body: { "ip": "192.168.1.1" }   (optional — random IP used if omitted)
    """
    body = request.get_json(silent=True) or {}
    ip = body.get("ip") or generateRandomIP()

    try:
        result = LoadBalancer(ip)
        return jsonify(result), 200 if result["status"] == "routed" else 429
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 503


# ─────────────────────────────────────────────
#  POST /simulate
#  Simulate N random incoming requests
# ─────────────────────────────────────────────
@api.route("/simulate", methods=["POST"])
def simulate():
    """
    Simulate traffic.
    Body: { "count": 10 }
    """
    body = request.get_json(silent=True) or {}
    count = int(body.get("count", 5))
    count = min(count, 100)  # cap at 100 for safety

    results = []
    for _ in range(count):
        ip = generateRandomIP()
        try:
            result = LoadBalancer(ip)
            results.append(result)
        except RuntimeError as e:
            results.append({"status": "error", "message": str(e)})
            break

    return jsonify({"simulated": len(results), "results": results}), 200


# ─────────────────────────────────────────────
#  GET /metrics
#  Request distribution dashboard
# ─────────────────────────────────────────────
@api.route("/metrics", methods=["GET"])
def metrics():
    """Return request counts, percentages, and recent request log."""
    return jsonify(get_metrics()), 200


# ─────────────────────────────────────────────
#  DELETE /metrics/reset
#  Clear all metrics
# ─────────────────────────────────────────────
@api.route("/metrics/reset", methods=["DELETE"])
def metrics_reset():
    reset_metrics()
    return jsonify({"status": "ok", "message": "Metrics cleared."}), 200


# ─────────────────────────────────────────────
#  GET /health
#  Node health status
# ─────────────────────────────────────────────
@api.route("/health", methods=["GET"])
def health():
    """Return health + weight status of all nodes."""
    return jsonify({"nodes": get_health_status()}), 200


# ─────────────────────────────────────────────
#  PATCH /health/<node_name>
#  Toggle a node online or offline
# ─────────────────────────────────────────────
@api.route("/health/<node_name>", methods=["PATCH"])
def update_health(node_name):
    """
    Set a node's health.
    Body: { "healthy": false }
    """
    body = request.get_json(silent=True) or {}
    if "healthy" not in body:
        return jsonify({"error": "Missing 'healthy' field (true/false)"}), 400

    found = set_node_health(node_name, bool(body["healthy"]))
    if not found:
        return jsonify({"error": f"Node '{node_name}' not found."}), 404

    return jsonify({"status": "ok", "node": node_name, "healthy": body["healthy"]}), 200


# ─────────────────────────────────────────────
#  GET /nodes
#  List all registered nodes
# ─────────────────────────────────────────────
@api.route("/nodes", methods=["GET"])
def nodes():
    """Return full node list with name, weight, and health."""
    return jsonify({"nodes": NODES}), 200


# ─────────────────────────────────────────────
#  GET /
#  API index / welcome
# ─────────────────────────────────────────────
@api.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "Rendezvous Load Balancer",
        "version": "1.0.0",
        "algorithm": "Rendezvous Hashing (HRW)",
        "endpoints": {
            "POST /route": "Route an IP (body: {ip})",
            "POST /simulate": "Simulate N requests (body: {count})",
            "GET  /metrics": "Request distribution dashboard",
            "DELETE /metrics/reset": "Clear metrics",
            "GET  /health": "Node health status",
            "PATCH /health/<node>": "Set node health (body: {healthy})",
            "GET  /nodes": "List all nodes",
        }
    }), 200
