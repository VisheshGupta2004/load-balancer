"""
load_balancer.py
----------------
Implements Rendezvous Hashing (Highest Random Weight) to replace
the original random-node routing strategy.

Why Rendezvous Hashing?
  - Same IP always reaches the same node (deterministic)
  - Stable even when nodes are added or removed (~1/N IPs remap)
  - Weighted routing is a single multiplier — no extra structures
  - Simpler to implement and read than Consistent Hashing

Original JS structure preserved: generateRandomIP → LoadBalancer → identifyNode
"""

import hashlib
import random
import time
from datetime import datetime
from collections import defaultdict


# ─────────────────────────────────────────────
#  Node Registry
#  Each node has a name, weight, and health flag
# ─────────────────────────────────────────────
NODES = [
    {"name": "Node-A", "weight": 3, "healthy": True},   # High priority
    {"name": "Node-B", "weight": 2, "healthy": True},   # Medium priority
    {"name": "Node-C", "weight": 1, "healthy": True},   # Low priority
]

# ─────────────────────────────────────────────
#  In-Memory Metrics Store
# ─────────────────────────────────────────────
metrics = defaultdict(int)          # request count per node
request_log = []                    # full request history
rate_limit_store = defaultdict(list) # timestamps per IP for rate limiting

RATE_LIMIT = 5        # max requests per IP
RATE_WINDOW = 60      # within this many seconds


# ─────────────────────────────────────────────
#  1. Random IP Generator  (preserved from original JS)
#     Array.from({length:4}, () => Math.floor(Math.random()*256)).join(".")
# ─────────────────────────────────────────────
def generateRandomIP():
    """Generate a random IPv4 address (mirrors original JS implementation)."""
    return ".".join(str(random.randint(0, 255)) for _ in range(4))


# ─────────────────────────────────────────────
#  2. Identify Node  (preserved from original JS)
#     console.log(`Incoming IP: ${ip} → Routed to: ${selectedNode}`)
# ─────────────────────────────────────────────
def identifyNode(ip, selectedNode):
    """Log which node received the incoming request."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}]  Incoming IP: {ip}  →  Routed to: {selectedNode}")


# ─────────────────────────────────────────────
#  Core: Rendezvous Hashing
#  score(ip, node) = weight × hash(ip + node_name)
#  Winner = node with highest score
# ─────────────────────────────────────────────
def _hrw_score(ip: str, node_name: str, weight: int) -> int:
    """Compute the weighted HRW score for an (ip, node) pair."""
    raw = hashlib.md5(f"{ip}-{node_name}".encode()).hexdigest()
    return weight * int(raw, 16)


def _get_healthy_nodes():
    """Return only the nodes currently marked healthy."""
    healthy = [n for n in NODES if n["healthy"]]
    if not healthy:
        raise RuntimeError("All nodes are down — no healthy nodes available.")
    return healthy


# ─────────────────────────────────────────────
#  3. Load Balancer  (replaces original random strategy)
#     Original: const randomIndex = Math.floor(Math.random() * nodes.length)
#     New:      Rendezvous Hashing — deterministic, stable on node changes
# ─────────────────────────────────────────────
def LoadBalancer(ip: str) -> dict:
    """
    Route an incoming IP to a node using Rendezvous (HRW) hashing.

    - Deterministic: same IP always hits the same node
    - Stable:        only ~1/N IPs remap when nodes are added/removed
    - Weighted:      higher-weight nodes attract proportionally more IPs
    - Fault-tolerant: unhealthy nodes are excluded from selection
    """

    # ── Rate Limit Check ──────────────────────────────────────────────
    now = time.time()
    rate_limit_store[ip] = [
        t for t in rate_limit_store[ip] if now - t < RATE_WINDOW
    ]
    if len(rate_limit_store[ip]) >= RATE_LIMIT:
        return {
            "status": "rate_limited",
            "ip": ip,
            "message": f"Too many requests. Max {RATE_LIMIT} per {RATE_WINDOW}s.",
        }
    rate_limit_store[ip].append(now)

    # ── Rendezvous Hashing ────────────────────────────────────────────
    healthy_nodes = _get_healthy_nodes()
    selected_node = max(
        healthy_nodes,
        key=lambda node: _hrw_score(ip, node["name"], node["weight"])
    )
    node_name = selected_node["name"]

    # ── Metrics ───────────────────────────────────────────────────────
    metrics[node_name] += 1
    entry = {
        "ip": ip,
        "node": node_name,
        "timestamp": datetime.now().isoformat(),
        "weight": selected_node["weight"],
    }
    request_log.append(entry)

    # ── Keep this code to identify which node received the request ────
    identifyNode(ip, node_name)

    return {"status": "routed", "ip": ip, "node": node_name}


# ─────────────────────────────────────────────
#  4. Simulate Traffic  (mirrors original JS simulateTraffic)
#     for (let i = 0; i < requestCount; i++) { LoadBalancer(generateRandomIP()) }
# ─────────────────────────────────────────────
def simulateTraffic(requestCount: int = 5):
    """Simulate incoming traffic with random IPs (mirrors original JS)."""
    print(f"\n{'─'*55}")
    print(f"  Simulating {requestCount} incoming requests")
    print(f"{'─'*55}")
    for _ in range(requestCount):
        ip = generateRandomIP()
        LoadBalancer(ip)
    print(f"{'─'*55}\n")


# ─────────────────────────────────────────────
#  Health Check Utilities
# ─────────────────────────────────────────────
def set_node_health(node_name: str, status: bool):
    """Mark a node healthy (True) or unhealthy (False)."""
    for node in NODES:
        if node["name"] == node_name:
            node["healthy"] = status
            state = "ONLINE" if status else "OFFLINE"
            print(f"  [Health] {node_name} → {state}")
            return True
    return False


def get_health_status():
    """Return current health status of all nodes."""
    return [
        {"name": n["name"], "healthy": n["healthy"], "weight": n["weight"]}
        for n in NODES
    ]


# ─────────────────────────────────────────────
#  Metrics Utilities
# ─────────────────────────────────────────────
def get_metrics():
    """Return request distribution across all nodes."""
    total = sum(metrics.values())
    return {
        "total_requests": total,
        "distribution": {
            node: {
                "requests": metrics[node],
                "percentage": round((metrics[node] / total * 100), 1) if total else 0,
            }
            for node in metrics
        },
        "recent_requests": request_log[-10:],
    }


def reset_metrics():
    """Clear all in-memory metrics (useful for testing)."""
    metrics.clear()
    request_log.clear()
    rate_limit_store.clear()


# ─────────────────────────────────────────────
#  Run simulation when executed directly
# ─────────────────────────────────────────────
if __name__ == "__main__":
    simulateTraffic(10)
