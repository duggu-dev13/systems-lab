# Systems Lab: Progress Notes (Lab 1: Rate Limiter)

## 1. The big picture

**Final goal:** build an IRCTC-style multi-service system to learn system design. Not for deployment.

**Strategy:** build the small building blocks first, then assemble them.

```
systems-lab/
├── 01-rate-limiter/        <- we are here
├── 02-load-balancer/
├── 03-cache/
├── 04-distributed-lock/
├── 05-message-queue/
├── 06-saga-and-idempotency/
├── 07-api-gateway/
└── 08-irctc/
```

| Lab | IRCTC use |
|---|---|
| Rate limiter | Tatkal rush, bot protection |
| Load balancer | Spreading load across booking instances |
| Cache | Train search, availability counts |
| Distributed lock | Holding a seat during payment |
| Message queue | Notifications, waitlist promotion |
| Idempotency + saga | Payment succeeded but booking failed |
| API gateway | The front door |

---

## 2. Lab 1 plan

**Goal:** a rate limiter where algorithms can be swapped and compared with real numbers.

**Algorithms to build, in order:**
1. Fixed window (done)
2. Sliding window log (code given)
3. Sliding window counter
4. Token bucket
5. Redis-backed distributed version (Lua script for atomicity)

**Agile loop per sprint:** Plan -> Build -> Test -> Measure -> Retrospective.

**Later (not started yet):** Prometheus + Grafana metrics, k6 load tests, Redis, failure modes (fail open vs fail closed).

---

## 3. Environment

- OS: Windows, PowerShell
- Python with `uv` (`pyproject.toml`, `uv.lock`)
- Libraries: `fastapi`, `uvicorn`, `pytest`, `httpx`

### Final project layout

```
01-rate-limiter/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── limiters/
│       ├── __init__.py
│       ├── base.py
│       ├── fixed_window.py
│       └── sliding_log.py
├── tests/
│   ├── test_fixed_window.py
│   └── test_sliding_log.py
├── decisions.md
├── pyproject.toml
└── uv.lock
```

---

## 4. Code so far

### `app/limiters/base.py`: the common interface

```python
import time
from dataclasses import dataclass
from typing import Callable

@dataclass
class Decision:
    allowed: bool
    remaining: int
    retry_after: float   # seconds until the client may retry; 0 if allowed

class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock

    def check(self, key: str) -> Decision:
        raise NotImplementedError
```

The `clock` is injected so tests can fake time instead of sleeping.

### `app/limiters/fixed_window.py`

```python
import time
from .base import RateLimiter, Decision

class FixedWindowLimiter(RateLimiter):
    def __init__(self, limit, window_seconds, clock=time.monotonic):
        super().__init__(clock)
        self.limit = limit
        self.window = window_seconds
        self.counts = {}   # key -> (window_number, count_in_that_window)

    def check(self, key):
        now = self.clock()
        window_number = int(now // self.window)

        stored_window, count = self.counts.get(key, (window_number, 0))
        if stored_window != window_number:
            count = 0

        if count >= self.limit:
            retry_after = (window_number + 1) * self.window - now
            self.counts[key] = (window_number, count)
            return Decision(False, 0, retry_after)

        count += 1
        self.counts[key] = (window_number, count)
        return Decision(True, self.limit - count, 0)
```

### `app/main.py`: middleware + endpoint

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.limiters.fixed_window import FixedWindowLimiter

app = FastAPI()
limiter = FixedWindowLimiter(limit=5, window_seconds=10)

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    key = request.client.host
    decision = limiter.check(key)
    if not decision.allowed:
        return JSONResponse(
            {"error": "too many requests"},
            status_code=429,
            headers={"Retry-After": str(int(decision.retry_after) + 1)},
        )
    return await call_next(request)

@app.get("/api/ping")
def ping():
    return {"message": "pong"}
```

Middleware runs before every request, so one limiter protects all routes.

---

## 5. Tests

Shared helper used in the test files:

```python
class FakeClock:
    def __init__(self, t=0.0):
        self.t = t
    def __call__(self):
        return self.t
```

### `tests/test_fixed_window.py` (3 tests, all passing)

- `test_blocks_after_limit`: 5 allowed, then rejected.
- `test_different_users_are_independent`: each key has its own counter.
- `test_boundary_burst_bug`: 5 requests at t=9.9s and 5 more at t=10.1s all succeed. **10 requests in 0.2s under a "5 per 10s" limit.** This test passing documents the flaw.

Run all tests:

```powershell
python -m pytest -v
```

Expected: 7 passed once the sliding log tests are added.

---

## 6. How to run and verify (PowerShell)

Start the server:

```powershell
uvicorn app.main:app --port 8000
```

In a second terminal, send 8 requests:

```powershell
1..8 | ForEach-Object {
    try { (Invoke-WebRequest http://localhost:8000/api/ping -UseBasicParsing).StatusCode }
    catch { $_.Exception.Response.StatusCode.value__ }
}
```

Expected: five `200`s then three `429`s. **Confirmed working.**

---

## 7. Problems hit and fixes (Windows lessons)

| Problem | Cause | Fix |
|---|---|---|
| `Could not import module "app.main"` | `main.py` was in the project root, not in `app\` | `Move-Item main.py app\main.py` |
| Missing package files | `touch` doesn't exist in PowerShell | `New-Item app\__init__.py -ItemType File -Force` (same for `app\limiters\`) |
| `Missing opening '(' after keyword 'for'` | Pasted Linux `for ... do ... done` loop into PowerShell | Use `1..8 \| ForEach-Object { ... }` |
| Commands from guides don't match shell | Guides default to Linux/Mac syntax | Always use PowerShell equivalents |

Debug tip: `python -c "import app.main"` shows the real import error.

---

## 8. Decisions log (`decisions.md`)

```markdown
# Decisions

## Fixed window
- Good: very simple, one counter per client, cheap on memory.
- Bad: boundary burst. A client can send 5 requests at t=9.9s and 5 more at
  t=10.1s, getting 10 requests through in 0.2 seconds.

```

---

## 9. Key concepts learned

- A rate limiter needs a **key per client** (IP or user ID) and a **counter or log per time window**.
- Middleware lets one limiter protect every route.
- A **common interface** (`check(key) -> Decision`) makes algorithms swappable.
- An **injected fake clock** lets time-based logic be tested instantly, with no sleeping.
- The simplest algorithm (fixed window) has a real flaw; each next algorithm exists to fix a weakness of the previous one.
- Accuracy costs memory (sliding log), which motivates approximations.

---