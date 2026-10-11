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