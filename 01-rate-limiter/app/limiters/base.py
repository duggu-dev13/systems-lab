import time
from dataclasses import dataclass
from typing import Callable

@dataclass
class Decision:
    allowed: bool
    remaining: int
    retry_after: float   # seconds until the client may retry; 0 if allowed

class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock

    def check(self, key: str) -> Decision:
        raise NotImplementedError