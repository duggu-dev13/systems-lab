# systems-lab

Learning system design by building the pieces myself, from scratch, one small lab at a time.

The end goal is an **IRCTC-style train booking system** made of multiple services. It is not meant for deployment. The point is to understand how real multi-service architectures work. Instead of jumping straight into the big project, I'm first building each core building block on its own (rate limiter, load balancer, cache, and so on), breaking it on purpose, and measuring it. Then I'll assemble them.

## Roadmap

| Lab | Building block | Where it shows up in IRCTC | Status |
|---|---|---|---|
| [01-rate-limiter](./01-rate-limiter) | Fixed window, sliding window, token bucket, Redis-backed | Tatkal rush, bot protection | In progress |
| 02-load-balancer | Round robin, least connections, health checks, retries | Spreading load across booking instances | Planned |
| 03-cache | LRU, TTL, cache-aside, stampede prevention | Train search, availability counts | Planned |
| 04-distributed-lock | Redis `SET NX PX`, expiry, fencing tokens | Holding a seat during payment | Planned |
| 05-message-queue | In-memory queue, then Kafka/RabbitMQ | Notifications, waitlist promotion | Planned |
| 06-saga-and-idempotency | Idempotency keys, compensation, outbox | Payment succeeded but booking failed | Planned |
| 07-api-gateway | Rate limiter + load balancer + auth | The front door | Planned |
| 08-irctc | Everything wired together | The real project | Planned |

## How each lab works

Every lab follows the same loop:

```
Plan -> Build -> Test -> Measure -> Retrospective -> next sprint
```

Each lab documents three things: what problem it solves, how it works, and where it breaks. Trade-offs I run into are written down in a `decisions.md` file.

## Lab 01: Rate limiter

A small FastAPI server with one endpoint, `/api/ping`. If a client (identified by IP) sends too many requests in a time window, the server replies `429 Too Many Requests` with a `Retry-After` header.

Every algorithm implements the same interface, so they can be swapped and compared:

```python
limiter.check(key) -> Decision(allowed, remaining, retry_after)
```

### Algorithms

| Algorithm | Status | Idea | Weakness |
|---|---|---|---|
| Fixed window | Done | One counter per client per time window | Boundary burst: up to 2x the limit across a window edge |
| Sliding window log | Done | Store every request timestamp, drop old ones | Memory grows with the limit |
| Sliding window counter | Next | Two counters, weighted estimate | Approximate |
| Token bucket | Planned | Tokens refill at a steady rate, allows controlled bursts | Needs tuning of capacity and refill |
| Redis + Lua | Planned | Shared state, atomic check-and-update | Redis becomes a dependency (fail open or closed?) |

### Testing approach

The limiters take an injected clock, so tests can jump through time instantly instead of sleeping. This makes boundary cases easy to prove. For example, `test_boundary_burst_bug` shows the fixed window letting 10 requests through in 0.2 seconds under a "5 per 10 seconds" rule, and `test_boundary_burst_is_fixed` shows the sliding log rejecting the same traffic.

### Run it

Requires Python 3.11+.

```bash
cd 01-rate-limiter
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/Mac: source .venv/bin/activate
pip install fastapi uvicorn pytest httpx
uvicorn app.main:app --port 8000
```

Try it (PowerShell):

```powershell
1..8 | ForEach-Object {
    try { (Invoke-WebRequest http://localhost:8000/api/ping -UseBasicParsing).StatusCode }
    catch { $_.Exception.Response.StatusCode.value__ }
}
```

Linux/Mac:

```bash
for i in {1..8}; do curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/ping; done
```

Expected: five `200`s, then three `429`s.

### Run the tests

```bash
python -m pytest -v
```

### Project layout

```
01-rate-limiter/
├── app/
│   ├── main.py              # FastAPI app + rate limit middleware
│   └── limiters/
│       ├── base.py          # RateLimiter interface and Decision
│       ├── fixed_window.py
│       └── sliding_log.py
├── tests/
│   ├── test_fixed_window.py
│   └── test_sliding_log.py
└── decisions.md             # trade-offs and notes
```

### Coming up in this lab

- Sliding window counter and token bucket
- Prometheus + Grafana metrics (allowed vs rejected, decision latency, p50/p99)
- k6 load tests (steady, over-limit, burst, boundary, many users)
- Redis version with a Lua script, including a deliberately racy version to show why atomicity matters
- Failure behavior: what happens when Redis is down
- A final comparison and a recommendation for the Tatkal rush

## What I'm learning

- Why a limiter needs a key per client and state per time window
- How to structure code so algorithms are swappable
- How to test time-dependent logic without waiting
- That accuracy, memory, and burst behavior trade off against each other

## Notes

Notes on each step, including problems hit and how they were fixed, are in each lab's `decisions.md`.