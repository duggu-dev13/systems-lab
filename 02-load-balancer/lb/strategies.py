import os


class Strategy:
    """Every strategy picks a backend, and is told when a request finishes."""

    def __init__(self, backends):
        self.backends = list(backends)

    def pick(self):
        raise NotImplementedError

    def release(self, backend):
        pass  # most strategies don't need to know when a request ends


class RoundRobin(Strategy):
    def __init__(self, backends):
        super().__init__(backends)
        self.i = 0

    def pick(self):
        backend = self.backends[self.i % len(self.backends)]
        self.i += 1
        return backend


class LeastConnections(Strategy):
    def __init__(self, backends):
        super().__init__(backends)
        self.active = {b: 0 for b in self.backends}   # requests in flight
        self.i = 0                                    # rotates among ties

    def pick(self):
        fewest = min(self.active.values())
        candidates = [b for b in self.backends if self.active[b] == fewest]
        backend = candidates[self.i % len(candidates)]
        self.i += 1
        self.active[backend] += 1
        return backend

    def release(self, backend):
        self.active[backend] -= 1


class WeightedRoundRobin(Strategy):
    """Smooth weighted round robin (the algorithm nginx uses)."""

    def __init__(self, backends, weights):
        super().__init__(backends)
        self.weights = dict(zip(self.backends, weights))
        self.current = {b: 0 for b in self.backends}
        self.total = sum(weights)

    def pick(self):
        for b in self.backends:
            self.current[b] += self.weights[b]
        backend = max(self.backends, key=lambda b: self.current[b])
        self.current[backend] -= self.total
        return backend


def build_strategy(backends):
    name = os.getenv("LB_STRATEGY", "round_robin")
    if name == "round_robin":
        return RoundRobin(backends)
    if name == "least_connections":
        return LeastConnections(backends)
    if name == "weighted":
        weights = [int(w) for w in os.getenv("LB_WEIGHTS", "1,1,1").split(",")]
        if len(weights) != len(backends):
            raise ValueError("LB_WEIGHTS needs one number per backend")
        return WeightedRoundRobin(backends, weights)
    raise ValueError(f"unknown strategy: {name}")