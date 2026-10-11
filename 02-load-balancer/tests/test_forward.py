import asyncio

import httpx

from lb.forward import forward
from lb.strategies import RoundRobin, LeastConnections

B = ["a", "b", "c"]


class FakeResponse:
    status_code = 200


class FakeClient:
    """Pretends to be httpx.AsyncClient. Each backend either answers or raises."""

    def __init__(self, behaviour):
        self.behaviour = behaviour       # backend name -> exception to raise
        self.calls = []

    async def request(self, method, url, **kwargs):
        backend = url.split("/")[0]      # urls look like "a/api/ping"
        self.calls.append(backend)
        problem = self.behaviour.get(backend)
        if problem is not None:
            raise problem
        return FakeResponse()


def run(client, strategy, method="GET", max_attempts=3, unsafe=False):
    return asyncio.run(forward(
        client, strategy, method, "api/ping", None, b"", {},
        max_attempts=max_attempts, timeout=1.0, retry_unsafe=unsafe,
    ))


def test_dead_backend_is_retried_on_another():
    client = FakeClient({"a": httpx.ConnectError("refused")})
    r = run(client, RoundRobin(B))
    assert r.upstream is not None
    assert r.attempts == 2
    assert r.tried[0] == "a" and r.backend != "a"

def test_never_retries_the_same_backend_and_stops_at_max_attempts():
    client = FakeClient({x: httpx.ConnectError("refused") for x in B})
    r = run(client, RoundRobin(B))
    assert r.upstream is None
    assert r.attempts == 3
    assert sorted(r.tried) == B

def test_max_attempts_is_respected():
    client = FakeClient({x: httpx.ConnectError("refused") for x in B})
    r = run(client, RoundRobin(B), max_attempts=2)
    assert r.attempts == 2 and len(client.calls) == 2

def test_post_read_timeout_gets_exactly_one_attempt():
    client = FakeClient({x: httpx.ReadTimeout("slow") for x in B})
    r = run(client, RoundRobin(B), method="POST")
    assert r.attempts == 1 and len(client.calls) == 1

def test_post_read_timeout_with_unsafe_flag_hits_every_backend():
    client = FakeClient({x: httpx.ReadTimeout("slow") for x in B})
    r = run(client, RoundRobin(B), method="POST", unsafe=True)
    assert r.attempts == 3 and len(client.calls) == 3

def test_post_connect_error_is_retried():
    client = FakeClient({"a": httpx.ConnectError("refused")})
    r = run(client, RoundRobin(B), method="POST")
    assert r.upstream is not None and r.backend != "a"

def test_get_read_timeout_is_retried():
    client = FakeClient({"a": httpx.ReadTimeout("slow")})
    r = run(client, RoundRobin(B))
    assert r.upstream is not None and r.backend != "a"

def test_no_healthy_backend_means_no_attempt():
    strategy = RoundRobin(B)
    for name in B:
        strategy.set_healthy(name, False)
    r = run(FakeClient({}), strategy)
    assert r.tried == [] and r.upstream is None

def test_in_flight_counts_return_to_zero_after_retries():
    strategy = LeastConnections(B)
    client = FakeClient({"a": httpx.ConnectError("x"), "b": httpx.ConnectError("x")})
    r = run(client, strategy)
    assert r.backend == "c"
    assert all(count == 0 for count in strategy.active.values())