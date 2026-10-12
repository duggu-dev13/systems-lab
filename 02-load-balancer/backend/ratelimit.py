import os


def build_limiter(env=os.environ):
    """Build a limiter from environment variables. LIMIT=0 (the default) means off."""
    algorithm = env.get("ALGO", "fixed_window")
    limit = int(env.get("LIMIT", "0"))
    window = float(env.get("WINDOW", "1"))

    if limit <= 0:
        return None

    if algorithm == "fixed_window":
        from backend.limiters.fixed_window import FixedWindowLimiter
        return FixedWindowLimiter(limit, window)
    if algorithm == "sliding_log":
        from backend.limiters.sliding_log import SlidingLogLimiter
        return SlidingLogLimiter(limit, window)
    if algorithm == "sliding_counter":
        from backend.limiters.sliding_counter import SlidingCounterLimiter
        return SlidingCounterLimiter(limit, window)
    if algorithm == "token_bucket":
        from backend.limiters.token_bucket import TokenBucketLimiter
        return TokenBucketLimiter(capacity=limit, refill_per_sec=limit / window)
    raise ValueError(f"unknown algorithm: {algorithm}")


def client_key(headers, client_host):
    """Identify the client. Behind a proxy the TCP peer is the proxy, not the user."""
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return client_host