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
        if stored_window != window_number:     # a new window started
            count = 0

        if count >= self.limit:
            retry_after = (window_number + 1) * self.window - now
            self.counts[key] = (window_number, count)
            return Decision(False, 0, retry_after)

        count += 1
        self.counts[key] = (window_number, count)
        return Decision(True, self.limit - count, 0)