from lb.strategies import RoundRobin, LeastConnections, WeightedRoundRobin


# ---- Step 5: round robin ----

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


# ---- Step 6: least connections and weighted ----

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

# ---- Step 7: health awareness ----

def test_round_robin_skips_unhealthy():
    rr = RoundRobin(["a", "b", "c"])
    rr.set_healthy("b", False)
    assert [rr.pick() for _ in range(4)] == ["a", "c", "a", "c"]

def test_round_robin_returns_none_when_all_down():
    rr = RoundRobin(["a", "b", "c"])
    for name in ["a", "b", "c"]:
        rr.set_healthy(name, False)
    assert rr.pick() is None

def test_least_connections_skips_unhealthy():
    lc = LeastConnections(["a", "b", "c"])
    lc.set_healthy("a", False)
    picks = [lc.pick() for _ in range(6)]
    assert "a" not in picks
    assert picks.count("b") == 3 and picks.count("c") == 3

def test_weighted_skips_unhealthy_and_recovers():
    w = WeightedRoundRobin(["a", "b", "c"], [3, 1, 1])
    w.set_healthy("a", False)
    picks = [w.pick() for _ in range(10)]
    assert "a" not in picks
    assert picks.count("b") == 5 and picks.count("c") == 5
    w.set_healthy("a", True)
    cycle = [w.pick() for _ in range(5)]
    assert cycle.count("a") == 3 and cycle.count("b") == 1 and cycle.count("c") == 1