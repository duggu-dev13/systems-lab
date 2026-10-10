import pytest
from app.limiters.sliding_counter import SlidingCounterLimiter

class FakeClock:
    def __init__(self, t=0.0):
        self.t = t
    def __call__(self):
        return self.t

def test_blocks_after_limit():
    limiter = SlidingCounterLimiter(limit=5, window_seconds=10, clock=FakeClock())
    results = [limiter.check("alice").allowed for _ in range(7)]
    assert results == [True] * 5 + [False] * 2

def test_boundary_burst_is_fixed():
    clock = FakeClock(t=9.9)
    limiter = SlidingCounterLimiter(limit=5, window_seconds=10, clock=clock)
    first_batch = [limiter.check("alice").allowed for _ in range(5)]

    clock.t = 10.1   # the moment that fooled the fixed window
    second_batch = [limiter.check("alice").allowed for _ in range(5)]

    assert all(first_batch)
    assert not any(second_batch)

def test_recovers_gradually():
    clock = FakeClock(t=9.9)
    limiter = SlidingCounterLimiter(limit=5, window_seconds=10, clock=clock)
    for _ in range(5):
        limiter.check("alice")

    clock.t = 15.0   # halfway through the next window: estimate = 5*0.5 + current
    results = [limiter.check("alice").allowed for _ in range(3)]
    assert results == [True, True, False]   # only 2 fit, not all 5

def test_forgets_after_idle():
    clock = FakeClock(t=0)
    limiter = SlidingCounterLimiter(limit=5, window_seconds=10, clock=clock)
    for _ in range(5):
        limiter.check("alice")

    clock.t = 25.0   # two full windows later
    results = [limiter.check("alice").allowed for _ in range(5)]
    assert all(results)

def test_retry_after_is_accurate():
    clock = FakeClock(t=9.9)
    limiter = SlidingCounterLimiter(limit=5, window_seconds=10, clock=clock)
    for _ in range(5):
        limiter.check("alice")

    clock.t = 15.0
    limiter.check("alice")
    limiter.check("alice")
    decision = limiter.check("alice")
    assert not decision.allowed
    assert decision.retry_after == pytest.approx(1.0)

    clock.t = 15.0 + decision.retry_after + 0.01
    assert limiter.check("alice").allowed