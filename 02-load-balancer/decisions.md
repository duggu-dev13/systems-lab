# Decisions

## Reverse proxy + round robin
- Strategy is a separate class from the proxy, so other strategies can be
  swapped in without changing the proxy code.
- Round robin is perfectly even in request COUNT, but it ignores how long
  each request takes and whether a backend is alive.
- With one backend dead, a third of requests fail (observed: every 3rd
  request returned 502). Round robin has no failure awareness.
- x-forwarded-for is added so backends (and later, the rate limiter) can see
  the real client IP, not the proxy's IP.
- No lock in pick(): safe because asyncio runs one request at a time inside
  it. This stops being true once state is shared between processes.