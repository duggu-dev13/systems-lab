from lb.strategies import RoundRobin

def test_cycles_in_order():
    rr = RoundRobin(["a", "b", "c"])
    assert [rr.pick() for _ in range(6)] == ["a", "b", "c", "a", "b", "c"]

def test_single_backend():
    rr = RoundRobin(["a"])
    assert [rr.pick() for _ in range(3)] == ["a", "a", "a"]

def test_even_distribution():
    rr = RoundRobin(["a", "b", "c"])
    picks = [rr.pick() for _ in range(300)]
    assert picks.count("a") == picks.count("b") == picks.count("c") == 100

from lb.strategies import LeastConnections, WeightedRoundRobin

def test_least_connections_avoids_busy_backend():
    lc = LeastConnections(["a", "b", "c"])
    busy = lc.pick()                        # one request now in flight there
    next_two = [lc.pick(), lc.pick()]
    assert busy not in next_two

def test_least_connections_release_frees_backend():
    lc = LeastConnections(["a", "b"])
    first = lc.pick()
    lc.release(first)
    assert lc.active == {"a": 0, "b": 0}

def test_least_connections_rotates_when_all_idle():
    lc = LeastConnections(["a", "b", "c"])
    seen = set()
    for _ in range(6):
        b = lc.pick()
        seen.add(b)
        lc.release(b)
    assert seen == {"a", "b", "c"}

def test_weighted_matches_weights():
    w = WeightedRoundRobin(["a", "b", "c"], [3, 1, 1])
    picks = [w.pick() for _ in range(500)]
    assert picks.count("a") == 300
    assert picks.count("b") == 100
    assert picks.count("c") == 100

def test_weighted_is_smooth():
    w = WeightedRoundRobin(["a", "b", "c"], [3, 1, 1])
    assert [w.pick() for _ in range(5)] == ["a", "b", "a", "c", "a"]