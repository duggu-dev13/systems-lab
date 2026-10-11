from dataclasses import dataclass, field

import httpx

from lb.retry import may_retry


@dataclass
class Result:
    upstream: object = None                  # the backend's response, if one succeeded
    backend: str = None                      # which backend produced it
    attempts: int = 0
    tried: list = field(default_factory=list)
    error: Exception = None                  # the last failure, if none succeeded


async def forward(client, strategy, method, path, params, body, headers,
                  *, max_attempts, timeout, retry_unsafe=False):
    result = Result()
    for attempt in range(1, max_attempts + 1):
        backend = strategy.pick(exclude=result.tried)   # never retry the same backend
        if backend is None:
            break
        result.tried.append(backend)
        result.attempts = attempt
        try:
            result.upstream = await client.request(
                method, f"{backend}/{path}",
                params=params, content=body, headers=headers, timeout=timeout,
            )
            result.backend = backend
            return result
        except httpx.HTTPError as exc:
            result.error = exc
            if not may_retry(method, exc, retry_unsafe):
                break
        finally:
            strategy.release(backend)
    return result