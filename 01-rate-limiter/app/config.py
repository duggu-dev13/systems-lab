import os
from app.limiters.fixed_window import FixedWindowLimiter
from app.limiters.sliding_log import SlidingLogLimiter
from app.limiters.sliding_counter import SlidingCounterLimiter
from app.limiters.token_bucket import TokenBucketLimiter

ALGORITHM = os.getenv("ALGO", "fixed_window")
LIMIT = int(os.getenv("LIMIT", "100"))
WINDOW = float(os.getenv("WINDOW", "1"))

def build_limiter():
    if ALGORITHM == "fixed_window":
        return FixedWindowLimiter(LIMIT, WINDOW)
    if ALGORITHM == "sliding_log":
        return SlidingLogLimiter(LIMIT, WINDOW)
    if ALGORITHM == "sliding_counter":
        return SlidingCounterLimiter(LIMIT, WINDOW)
    if ALGORITHM == "token_bucket":
        return TokenBucketLimiter(capacity=LIMIT, refill_per_sec=LIMIT / WINDOW)
    raise ValueError(f"unknown algorithm: {ALGORITHM}")