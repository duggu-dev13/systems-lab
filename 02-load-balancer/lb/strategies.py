class RoundRobin:
    def __init__(self, backends):
        self.backends = list(backends)
        self.i = 0

    def pick(self):
        backend = self.backends[self.i % len(self.backends)]
        self.i += 1
        return backend