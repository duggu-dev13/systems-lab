from app.limiters.fixed_window import FixedWindowLimiter

class FakeClock:
    def __init__(self, t=0.0):
        self.t = t
    def __call__(self):
        return self.t

def test_blocks_after_limit():
    clock = FakeClock()
    limiter = FixedWindowLimiter(limit=5, window_seconds=10, clock=clock)
    results = [limiter.check("alice").allowed for _ in range(7)]
    assert results == [True] * 5 + [False] * 2

def test_different_users_are_independent():
    limiter = FixedWindowLimiter(limit=1, window_seconds=10, clock=FakeClock())
    assert limiter.check("alice").allowed
    assert limiter.check("bob").allowed

def test_boundary_burst_bug():
    clock = FakeClock(t=9.9)                      # just before the window ends
    limiter = FixedWindowLimiter(limit=5, window_seconds=10, clock=clock)
    first_batch = [limiter.check("alice").allowed for _ in range(5)]

    clock.t = 10.1                                # just after the new window starts
    second_batch = [limiter.check("alice").allowed for _ in range(5)]

    assert all(first_batch) and all(second_batch)  # 10 requests in 0.2 seconds!