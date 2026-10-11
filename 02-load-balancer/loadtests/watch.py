import asyncio
import time
from collections import Counter

import httpx

URL = "http://127.0.0.1:8000/api/ping"
RATE = 10          # requests per second
DURATION = 40      # seconds


async def one(client, current):
    try:
        r = await client.get(URL)
        key = r.json()["served_by"] if r.status_code == 200 else f"HTTP {r.status_code}"
        if int(r.headers.get("x-attempts", "1")) > 1:
            current["(retried)"] += 1          # served only after a retry
    except Exception:
        key = "error"
    current[key] += 1


async def reporter(current, start):
    while True:
        await asyncio.sleep(1)
        print(f"t={time.perf_counter() - start:3.0f}s  {dict(sorted(current.items()))}", flush=True)
        current.clear()


async def main():
    current = Counter()
    start = time.perf_counter()
    report = asyncio.create_task(reporter(current, start))
    async with httpx.AsyncClient(timeout=10) as client:
        tasks = []
        for k in range(RATE * DURATION):
            await asyncio.sleep(max(0, start + k / RATE - time.perf_counter()))
            tasks.append(asyncio.create_task(one(client, current)))
        await asyncio.gather(*tasks)
    await asyncio.sleep(1)
    report.cancel()


asyncio.run(main())