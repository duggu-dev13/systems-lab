from lb.strategies import RoundRobin, LeastConnections


def test_round_robin_exclude_skips_backend():
    rr = RoundRobin(["a", "b", "c"])
    assert rr.pick(exclude=["a"]) in ("b", "c")

def test_round_robin_all_excluded_returns_none():
    rr = RoundRobin(["a", "b", "c"])
    assert rr.pick(exclude=["a", "b", "c"]) is None

def test_least_connections_exclude():
    lc = LeastConnections(["a", "b", "c"])
    assert lc.pick(exclude=["a", "b"]) == "c"

def test_round_robin_retry_walks_to_next_backend():
    rr = RoundRobin(["a", "b", "c"])
    assert rr.pick() == "a"
    assert rr.pick() == "b"
    assert rr.pick(exclude=["b"]) == "c"     # the retry moves on to the next backend
    assert rr.pick() == "a"                  # and the rotation continues from there