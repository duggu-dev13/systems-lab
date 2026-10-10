import pytest
from app.limiters.token_bucket import TokenBucketLimiter

class FakeClock:
    def __init__(self, t=0.0):
        self.t = t
    def __call__(self):
        return self.t

def test_blocks_after_limit():
    limiter = TokenBucketLimiter(capacity=5, refill_per_sec=0.5, clock=FakeClock())
    results = [limiter.check("alice").allowed for _ in range(7)]
    assert results == [True] * 5 + [False] * 2

def test_different_users_are_independent():
    limiter = TokenBucketLimiter(capacity=1, refill_per_sec=0.1, clock=FakeClock())
    assert limiter.check("alice").allowed
    assert limiter.check("bob").allowed

def test_boundary_burst_is_fixed():
    clock = FakeClock(t=9.9)
    limiter = TokenBucketLimiter(capacity=5, refill_per_sec=0.5, clock=clock)
    first_batch = [limiter.check("alice").allowed for _ in range(5)]

    clock.t = 10.1   # only 0.2s passed, so just 0.1 of a token came back
    second_batch = [limiter.check("alice").allowed for _ in range(5)]

    assert all(first_batch)
    assert not any(second_batch)

def test_refills_at_steady_rate():
    clock = FakeClock(t=0)
    limiter = TokenBucketLimiter(capacity=5, refill_per_sec=1, clock=clock)
    for _ in range(5):
        limiter.check("alice")           # drain the bucket
    assert not limiter.check("alice").allowed

    clock.t = 1.0                         # exactly one token has dripped in
    assert limiter.check("alice").allowed
    assert not limiter.check("alice").allowed

    clock.t = 2.0                         # and one more
    assert limiter.check("alice").allowed

def test_idle_client_cannot_save_up_beyond_capacity():
    clock = FakeClock(t=0)
    limiter = TokenBucketLimiter(capacity=5, refill_per_sec=1, clock=clock)
    limiter.check("alice")

    clock.t = 1000.0                      # idle for a very long time
    results = [limiter.check("alice").allowed for _ in range(8)]
    assert results == [True] * 5 + [False] * 3

def test_retry_after_is_accurate():
    clock = FakeClock(t=0)
    limiter = TokenBucketLimiter(capacity=2, refill_per_sec=0.5, clock=clock)
    limiter.check("alice")
    limiter.check("alice")                # bucket is now empty

    clock.t = 0.5                         # 0.25 tokens so far
    decision = limiter.check("alice")
    assert not decision.allowed
    assert decision.retry_after == pytest.approx(1.5)

    clock.t = 0.5 + decision.retry_after + 0.001
    assert limiter.check("alice").allowed

def test_long_run_rate_matches_refill_rate():
    clock = FakeClock(t=0)
    limiter = TokenBucketLimiter(capacity=5, refill_per_sec=0.5, clock=clock)
    allowed = 0
    for i in range(1000):                 # 10 requests per second for 100 seconds
        clock.t = i * 0.1
        if limiter.check("alice").allowed:
            allowed += 1
    # burst of 5 + about 0.5 tokens/sec * 100 sec = roughly 55
    assert 53 <= allowed <= 56