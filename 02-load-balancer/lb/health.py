import asyncio
import os

import httpx

INTERVAL = float(os.getenv("HEALTH_INTERVAL", "1.0"))        # seconds between checks
TIMEOUT = float(os.getenv("HEALTH_TIMEOUT", "0.5"))          # per-check timeout
FAIL_THRESHOLD = int(os.getenv("HEALTH_FAIL", "3"))          # failures before DOWN
PASS_THRESHOLD = int(os.getenv("HEALTH_PASS", "2"))          # successes before UP


class HealthTracker:
    """Decides when a backend flips between UP and DOWN. Pure logic, no network."""

    def __init__(self, backends, fail_threshold=FAIL_THRESHOLD, pass_threshold=PASS_THRESHOLD):
        self.fail_threshold = fail_threshold
        self.pass_threshold = pass_threshold
        self.healthy = {b: True for b in backends}   # optimistic start
        self.streak = {b: 0 for b in backends}       # results that disagree with current status

    def record(self, backend, ok):
        """Feed one check result. Returns True if the backend's status flipped."""
        if ok == self.healthy[backend]:
            self.streak[backend] = 0                 # agrees with status: reset
            return False
        self.streak[backend] += 1
        needed = self.pass_threshold if ok else self.fail_threshold
        if self.streak[backend] >= needed:
            self.healthy[backend] = ok
            self.streak[backend] = 0
            return True
        return False


async def check_one(client, backend):
    try:
        r = await client.get(f"{backend}/health", timeout=TIMEOUT)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


async def health_loop(client, strategy, tracker):
    while True:
        results = await asyncio.gather(*(check_one(client, b) for b in strategy.backends))
        for backend, ok in zip(strategy.backends, results):
            if tracker.record(backend, ok):
                strategy.set_healthy(backend, ok)
                print(f"[health] {backend} is now {'UP' if ok else 'DOWN'}", flush=True)
        await asyncio.sleep(INTERVAL)