import time
from .base import RateLimiter, Decision

class TokenBucketLimiter(RateLimiter):
    def __init__(self, capacity, refill_per_sec, clock=time.monotonic):
        super().__init__(clock)
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec
        self.state = {}   # key -> (tokens, last_refill_time)

    def check(self, key):
        now = self.clock()

        # a client we haven't seen starts with a full bucket
        tokens, last = self.state.get(key, (self.capacity, now))

        # refill for the time that passed, but never above capacity
        tokens = min(self.capacity, tokens + (now - last) * self.refill_per_sec)

        if tokens < 1:
            self.state[key] = (tokens, now)
            retry_after = (1 - tokens) / self.refill_per_sec
            return Decision(False, 0, retry_after)

        tokens -= 1
        self.state[key] = (tokens, now)
        return Decision(True, int(tokens), 0)