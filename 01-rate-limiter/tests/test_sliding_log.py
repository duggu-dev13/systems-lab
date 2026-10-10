from app.limiters.sliding_log import SlidingLogLimiter

class FakeClock:
    def __init__(self, t=0.0):
        self.t = t
    def __call__(self):
        return self.t

def test_blocks_after_limit():
    limiter = SlidingLogLimiter(limit=5, window_seconds=10, clock=FakeClock())
    results = [limiter.check("alice").allowed for _ in range(7)]
    assert results == [True] * 5 + [False] * 2

def test_boundary_burst_is_fixed():
    clock = FakeClock(t=9.9)
    limiter = SlidingLogLimiter(limit=5, window_seconds=10, clock=clock)
    first_batch = [limiter.check("alice").allowed for _ in range(5)]

    clock.t = 10.1   # same moment that fooled the fixed window
    second_batch = [limiter.check("alice").allowed for _ in range(5)]

    assert all(first_batch)
    assert not any(second_batch)   # all rejected this time

def test_allows_again_after_window_passes():
    clock = FakeClock(t=0)
    limiter = SlidingLogLimiter(limit=5, window_seconds=10, clock=clock)
    for _ in range(5):
        limiter.check("alice")
    assert not limiter.check("alice").allowed

    clock.t = 10.5   # all 5 old requests have now left the window
    assert limiter.check("alice").allowed

def test_retry_after_is_accurate():
    clock = FakeClock(t=0)
    limiter = SlidingLogLimiter(limit=2, window_seconds=10, clock=clock)
    limiter.check("alice")          # at t=0
    clock.t = 3
    limiter.check("alice")          # at t=3
    clock.t = 4
    decision = limiter.check("alice")
    assert not decision.allowed
    assert decision.retry_after == 6   # oldest request (t=0) expires at t=10