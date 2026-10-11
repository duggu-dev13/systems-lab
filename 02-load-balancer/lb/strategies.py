import os


class Strategy:
    """Picks a backend for each request. Only healthy backends are eligible."""

    def __init__(self, backends):
        self.backends = list(backends)
        self.healthy = set(self.backends)

    def available(self, exclude=()):
        return [b for b in self.backends if b in self.healthy and b not in exclude]

    def set_healthy(self, backend, is_healthy):
        if is_healthy:
            self.healthy.add(backend)
        else:
            self.healthy.discard(backend)
        self.on_change()

    def on_change(self):
        pass

    def pick(self, exclude=()):
        """Return a backend, or None if none is eligible (all unhealthy or excluded)."""
        raise NotImplementedError

    def release(self, backend):
        pass  # most strategies don't need to know when a request ends


class RoundRobin(Strategy):
    def __init__(self, backends):
        super().__init__(backends)
        self.i = 0

    def pick(self, exclude=()):
        avail = self.available(exclude)
        if not avail:
            return None
        backend = avail[self.i % len(avail)]
        self.i += 1
        return backend


class LeastConnections(Strategy):
    def __init__(self, backends):
        super().__init__(backends)
        self.active = {b: 0 for b in self.backends}   # requests in flight
        self.i = 0                                    # rotates among ties

    def pick(self, exclude=()):
        avail = self.available(exclude)
        if not avail:
            return None
        fewest = min(self.active[b] for b in avail)
        candidates = [b for b in avail if self.active[b] == fewest]
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

    def on_change(self):
        # the set of eligible backends changed, so start the cycle fresh
        self.current = {b: 0 for b in self.backends}

    def pick(self, exclude=()):
        avail = self.available(exclude)
        if not avail:
            return None
        total = sum(self.weights[b] for b in avail)
        for b in avail:
            self.current[b] += self.weights[b]
        backend = max(avail, key=lambda b: self.current[b])
        self.current[backend] -= total
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