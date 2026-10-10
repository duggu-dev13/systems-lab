import time
from collections import deque
from .base import RateLimiter, Decision

class SlidingLogLimiter(RateLimiter):
    def __init__(self, limit, window_seconds, clock=time.monotonic):
        super().__init__(clock)
        self.limit = limit
        self.window = window_seconds
        self.logs = {}   # key -> deque of request timestamps

    def check(self, key):
        now = self.clock()
        log = self.logs.setdefault(key, deque())

        # 1. drop timestamps that fell out of the window
        while log and log[0] <= now - self.window:
            log.popleft()

        # 2. reject if the window is full
        if len(log) >= self.limit:
            retry_after = log[0] + self.window - now
            return Decision(False, 0, retry_after)

        # 3. otherwise record this request and allow it
        log.append(now)
        return Decision(True, self.limit - len(log), 0)