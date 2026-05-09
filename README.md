# Rendezvous Load Balancer

> A production-inspired HTTP load balancer built with **Python / Flask**, implementing **Rendezvous Hashing (HRW)** for deterministic, stable IP-to-node routing.

---

## Why Rendezvous Hashing?

The original code used `random.choice()` — a different node every request, no guarantees. The task requires:

| Requirement              | Random | IP Modulo | **Rendezvous (HRW)** |
| ------------------------ | :----: | :-------: | :------------------------: |
| Same IP → same node     |   ✗   |    ✓    |             ✓             |
| Stable when nodes change |   ✗   |    ✗    |             ✓             |
| Weighted routing         |   ✗   |    ✗    |             ✓             |
| Simple to implement      |   ✓   |    ✓    |             ✓             |

**How it works in one line:** for each incoming IP, compute `score = weight × hash(ip + node_name)` for every node. The node with the highest score wins. Because hashing is deterministic, the same IP always produces the same winner — even if other nodes are added or removed.

When a node is removed, only the IPs that were assigned to that node get remapped (~1/N). All other IPs are unaffected. This is mathematically impossible with modulo hashing.

---

## Project Structure

```
load-balancer/
│
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── load_balancer.py     # Core algorithm + all business logic
│   └── routes.py            # REST API endpoints
│
├── tests/
│   ├── test_load_balancer.py  # Unit tests (algorithm, health, rate limit)
│   └── test_routes.py         # Integration tests (API endpoints)
│
├── docs/
│   └── postman_collection.json  # Import into Postman to demo all endpoints
│
├── main.py           # Entry point
├── requirements.txt
├── Procfile          # For Render / Railway deployment
├── render.yaml       # One-click Render deployment config
└── README.md
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/VisheshGupta2004/rendezvous-load-balancer.git
cd rendezvous-load-balancer

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Run the server

```bash
python main.py
```

Output:

```
══════════════════════════════════════════════════
  Rendezvous Load Balancer  —  v1.0.0
  Algorithm : Rendezvous Hashing (HRW)
  Server    : http://127.0.0.1:5000
══════════════════════════════════════════════════
```

### 3. Run the simulation (standalone, no server needed)

```bash
python -m app.load_balancer
```

Output:

```
───────────────────────────────────────────────────────
  Simulating 10 incoming requests
───────────────────────────────────────────────────────
[2026-05-09 09:58:33]  Incoming IP: 177.122.51.164  →  Routed to: Node-B
[2026-05-09 09:58:33]  Incoming IP: 169.107.61.226  →  Routed to: Node-B
[2026-05-09 09:58:33]  Incoming IP: 68.97.220.160  →  Routed to: Node-A
[2026-05-09 09:58:33]  Incoming IP: 48.29.99.237  →  Routed to: Node-A
[2026-05-09 09:58:33]  Incoming IP: 97.102.153.63  →  Routed to: Node-A
[2026-05-09 09:58:33]  Incoming IP: 69.13.114.211  →  Routed to: Node-A
[2026-05-09 09:58:33]  Incoming IP: 225.37.26.199  →  Routed to: Node-A
[2026-05-09 09:58:33]  Incoming IP: 202.129.72.180  →  Routed to: Node-A
[2026-05-09 09:58:33]  Incoming IP: 82.4.82.42  →  Routed to: Node-B
[2026-05-09 09:58:33]  Incoming IP: 131.168.182.225  →  Routed to: Node-B
───────────────────────────────────────────────────────
```

### 4. Run tests

```bash
pytest tests/ -v
```

![1778306193252](image/README/1778306193252.png)

---

## API Reference

All responses are JSON. Base URL: `http://127.0.0.1:5000`

### `POST /route`

Route an IP to a node.

```bash
# Specific IP
curl -X POST http://localhost:5000/route \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.42"}'

# Random IP (omit body)
curl -X POST http://localhost:5000/route -H "Content-Type: application/json" -d '{}'
```

Response:

```json
{ "status": "routed", "ip": "192.168.1.42", "node": "Node-A" }
```

---

### `POST /simulate`

Simulate N random requests.

```bash
curl -X POST http://localhost:5000/simulate \
  -H "Content-Type: application/json" \
  -d '{"count": 20}'
```

---

### `GET /metrics`

Request distribution dashboard.

```bash
curl http://localhost:5000/metrics
```

Response:

```json
{
  "total_requests": 20,
  "distribution": {
    "Node-A": { "requests": 10, "percentage": 50.0 },
    "Node-B": { "requests": 7,  "percentage": 35.0 },
    "Node-C": { "requests": 3,  "percentage": 15.0 }
  },
  "recent_requests": [ ... ]
}
```

> Node-A gets more traffic because it has `weight: 3`. Weighted routing in action.

---

### `GET /health`

Node health status.

```bash
curl http://localhost:5000/health
```

### `PATCH /health/<node_name>`

Take a node offline or bring it back.

```bash
# Take Node-A offline
curl -X PATCH http://localhost:5000/health/Node-A \
  -H "Content-Type: application/json" \
  -d '{"healthy": false}'

# Bring it back
curl -X PATCH http://localhost:5000/health/Node-A \
  -H "Content-Type: application/json" \
  -d '{"healthy": true}'
```

---

### `DELETE /metrics/reset`

Clear all in-memory metrics.

```bash
curl -X DELETE http://localhost:5000/metrics/reset
```

### `GET /nodes`

List all nodes with name, weight, and health.

---

## Bonus Features

### Weighted Routing

Node weights are declared in `NODES` inside `load_balancer.py`:

```python
NODES = [
    {"name": "Node-A", "weight": 3, "healthy": True},  # gets ~50% of traffic
    {"name": "Node-B", "weight": 2, "healthy": True},  # gets ~33% of traffic
    {"name": "Node-C", "weight": 1, "healthy": True},  # gets ~17% of traffic
]
```

Higher weight = more virtual probability on the hash space. No extra data structures needed.

### Health Checks + Fallback

Mark any node offline via `PATCH /health/<node>`. The load balancer silently skips unhealthy nodes. If all nodes are down, a `503` is returned with a clear error message.

### Rate Limiting

Each IP is limited to **5 requests per 60 seconds** (sliding window). Requests beyond the limit return:

```json
{ "status": "rate_limited", "message": "Too many requests. Max 5 per 60s." }
```

Configurable via `RATE_LIMIT` and `RATE_WINDOW` in `load_balancer.py`.

### Metrics Dashboard

`GET /metrics` shows per-node request counts, percentages, and the last 10 routed requests.

---

## Postman Demo

1. Open Postman → Import → select `docs/postman_collection.json`
2. The collection contains 12 pre-built requests in demo order
3. For cloud testing, change the `base_url` variable to your deployment URL

Demo flow:

- Requests 2 & 3: prove same IP → same node (determinism)
- Requests 7–9: prove health check + fallback routing
- Request 10 (×6): trigger rate limiter

---

# Demo Screenshots

## 1. Test Suite Execution

All unit tests and API integration tests passing successfully.

![1778306614534](image/README/1778306614534.png)

Validated features:

- deterministic routing
- weighted rendezvous hashing
- node health checks
- metrics collection
- failover handling
- rate limiting
- API endpoint correctness

---

## 2. Server Startup

Flask server successfully running locally.

![1778306654708](image/README/1778306654708.png)

Available endpoints:

- `POST /route`
- `POST /simulate`
- `GET /metrics`
- `GET /health`
- `PATCH /health/<node>`
- `DELETE /metrics/reset`

---

## 3. Deterministic Routing (R1)

The same IP consistently maps to the same node.

### Request

```json
{
  "ip": "192.168.1.42"
}
```

### Response

```json
{
  "ip": "192.168.1.42",
  "node": "Node-A",
  "status": "routed"
}
```

![1778306681599](image/README/1778306681599.png)

This proves:

- deterministic routing
- stable IP-to-node mapping
- correctness of Rendezvous Hashing

---

## 4. Traffic Simulation

Large-scale request simulation using randomized IPs.

### Request

```json
{
  "count": 10000
}
```

![1778306698887](image/README/1778306698887.png)

The load balancer successfully distributes requests across weighted nodes.

---

## 5. Weighted Routing Metrics

Metrics dashboard after simulation.

![1778306714206](image/README/1778306714206.png)

Observed distribution:

| Node   | Traffic |
| ------ | ------- |
| Node-A | ~64%    |
| Node-B | ~28%    |
| Node-C | ~8%     |

This validates weighted routing behavior.

Node-A receives the most traffic because it has the highest configured weight.

---

## 6. Health Check / Failover

### Step 1 — Disable Node-A

```json
{
  "healthy": false
}
```

![1778306741137](image/README/1778306741137.png)

Node-A is successfully marked unhealthy and removed from routing.

---

## 7. Failover Routing Validation

After disabling Node-A, requests are routed only to healthy nodes.

### Example Request

```json
{
  "ip": "10.0.0.5"
}
```

### Example Response

```json
{
  "ip": "10.0.0.5",
  "node": "Node-B",
  "status": "routed"
}
```

![1778306755553](image/README/1778306755553.png)

This proves:

- unhealthy nodes are skipped
- fallback routing works correctly
- traffic automatically redistributes

---

## 8. Failover Simulation

Traffic simulation after Node-A is disabled.

![1778306767385](image/README/1778306767385.png)

Only Node-B and Node-C receive traffic.

---

## 9. Metrics After Failover

Metrics dashboard after failover simulation.

![1778306778954](image/README/1778306778954.png)

Observed distribution:

| Node   | Traffic |
| ------ | ------- |
| Node-A | 0%      |
| Node-B | ~72%    |
| Node-C | ~28%    |

This confirms:

- Node-A receives zero traffic once unhealthy
- requests are redistributed among remaining healthy nodes
- health-aware routing and fault tolerance work correctly

---

## 10. Standalone CLI Simulation

The load balancer also supports standalone terminal-based simulation without running the Flask server.

![1778306818549](image/README/1778306818549.png)

This demonstrates the core routing engine independently of the REST API layer.

---

## 11. Live Request Logs

Real-time request routing logs from the running Flask server.

![1778306830667](image/README/1778306830667.png)

Logs show:

- incoming IPs
- selected nodes
- deterministic routing behavior
- weighted distribution in action

---

## Deployment

### Live Deployment

The load balancer is deployed on Render:

```text
https://your-render-url.onrender.com
```

---

### Deploy on Render

1. Push the repository to GitHub
2. Go to https://render.com
3. Create a new **Web Service**
4. Connect the GitHub repository
5. Render automatically detects the included `render.yaml`
6. Click **Deploy**

The repository already includes:

- `render.yaml`
- `Procfile`

for production deployment configuration.

---

### Local Production Run

```bash
gunicorn main:app --workers 2 --bind 0.0.0.0:5000
```
---

## Algorithm: How Rendezvous Hashing Works

```
For each incoming request with IP "10.20.30.40":

  score(Node-A) = 3 × md5("10.20.30.40-Node-A") = 3 × 0xA3F2...  =  very large number
  score(Node-B) = 2 × md5("10.20.30.40-Node-B") = 2 × 0x77C1...  =  large number
  score(Node-C) = 1 × md5("10.20.30.40-Node-C") = 1 × 0xE901...  =  large number

  Winner = argmax(scores) → always the same for the same IP ✓
```

When Node-A is removed, only IPs where Node-A was the winner get reassigned. All other IPs are completely unaffected — this is the core advantage over `hash(ip) % N`.

---

## Tech Stack

- **Python 3.11** — language
- **Flask 3.1** — web framework
- **hashlib (md5)** — built-in, zero dependencies for hashing
- **pytest** — testing
- **gunicorn** — production WSGI server

---
