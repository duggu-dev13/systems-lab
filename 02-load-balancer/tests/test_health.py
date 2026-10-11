from lb.health import HealthTracker

B = ["a", "b", "c"]

def test_needs_three_failures_to_go_down():
    t = HealthTracker(B, fail_threshold=3, pass_threshold=2)
    assert t.record("a", False) is False
    assert t.record("a", False) is False
    assert t.healthy["a"]
    assert t.record("a", False) is True          # third failure flips it
    assert not t.healthy["a"]

def test_single_blip_is_ignored():
    t = HealthTracker(B, 3, 2)
    t.record("b", False)
    t.record("b", False)
    t.record("b", True)                          # success resets the streak
    assert t.record("b", False) is False
    assert t.healthy["b"]

def test_needs_two_passes_to_come_back():
    t = HealthTracker(B, 3, 2)
    for _ in range(3):
        t.record("c", False)
    assert not t.healthy["c"]
    assert t.record("c", True) is False
    assert not t.healthy["c"]
    assert t.record("c", True) is True
    assert t.healthy["c"]

def test_failure_during_recovery_resets_streak():
    t = HealthTracker(B, 3, 2)
    for _ in range(3):
        t.record("c", False)
    t.record("c", True)
    t.record("c", False)                         # relapse
    assert t.record("c", True) is False          # streak restarted
    assert not t.healthy["c"]