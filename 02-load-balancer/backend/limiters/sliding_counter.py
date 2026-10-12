import time
from .base import RateLimiter, Decision

class SlidingCounterLimiter(RateLimiter):
    def __init__(self, limit, window_seconds, clock=time.monotonic):
        super().__init__(clock)
        self.limit = limit
        self.window = window_seconds
        self.state = {}   # key -> (window_number, current_count, previous_count)

    def check(self, key):
        now = self.clock()
        window_number = int(now // self.window)
        elapsed = (now % self.window) / self.window   # 0.0 to 1.0 into this window

        w, cur, prev = self.state.get(key, (window_number, 0, 0))

        # roll the windows forward if time has moved on
        if w != window_number:
            if w == window_number - 1:
                prev, cur = cur, 0        # last window becomes "previous"
            else:
                prev, cur = 0, 0          # idle for 2+ windows: forget everything

        estimate = prev * (1 - elapsed) + cur

        if estimate + 1 > self.limit:
            self.state[key] = (window_number, cur, prev)
            return Decision(False, 0, self._retry_after(cur, prev, elapsed))

        cur += 1
        self.state[key] = (window_number, cur, prev)
        remaining = max(0, int(self.limit - (prev * (1 - elapsed) + cur)))
        return Decision(True, remaining, 0)

    def _retry_after(self, cur, prev, elapsed):
        # Case 1: the estimate drops below the limit later in this same window
        if cur < self.limit and prev > 0:
            e = 1 - (self.limit - cur - 1) / prev
            return max(0.0, (e - elapsed) * self.window)
        # Case 2: must wait for the next window, then for it to decay
        e = max(0.0, 1 - (self.limit - 1) / cur)
        return (1 - elapsed + e) * self.window