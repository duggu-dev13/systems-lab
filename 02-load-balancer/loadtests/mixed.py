import asyncio
import time
from collections import Counter

import httpx

URL = "http://127.0.0.1:8000"
N = 45               # total requests
GAP = 0.2            # seconds between requests (5 req/s)
SLOW_EVERY = 3       # every 3rd request is slow
SLOW_DELAY = 2.0     # seconds


async def one(client, k, out):
    slow = k % SLOW_EVERY == 0
    path = f"/slow?delay={SLOW_DELAY}" if slow else "/api/ping"
    t0 = time.perf_counter()
    try:
        r = await client.get(URL + path)
        ok = r.status_code == 200
        who = r.json().get("served_by", "?") if ok else f"HTTP {r.status_code}"
    except Exception:
        ok, who = False, "error"
    out.append((slow, who, time.perf_counter() - t0, ok))


def p95(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(0.95 * len(xs)))]


async def main():
    out = []
    async with httpx.AsyncClient(timeout=60) as client:
        tasks = []
        start = time.perf_counter()
        for k in range(N):
            await asyncio.sleep(max(0, start + k * GAP - time.perf_counter()))
            tasks.append(asyncio.create_task(one(client, k, out)))
        await asyncio.gather(*tasks)

    slow = [r for r in out if r[0]]
    fast = [r for r in out if not r[0]]
    print("slow requests per backend:", dict(Counter(r[1] for r in slow)))
    print("all requests per backend: ", dict(Counter(r[1] for r in out)))
    print(f"slow latency  avg {sum(r[2] for r in slow)/len(slow):.2f}s  "
          f"p95 {p95([r[2] for r in slow]):.2f}s  max {max(r[2] for r in slow):.2f}s")
    print(f"fast latency  avg {sum(r[2] for r in fast)/len(fast):.3f}s  "
          f"p95 {p95([r[2] for r in fast]):.3f}s")
    print("failures:", sum(1 for r in out if not r[3]))


asyncio.run(main())