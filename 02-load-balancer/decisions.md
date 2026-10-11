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

## Least connections and weighted
- Round robin balances request COUNT, not WORK. With every 3rd request slow
  and 3 backends, all slow requests landed on one backend (A: 15 of 15).
- Least connections balances current load, and fixed it: slow latency
  dropped from avg <paste> to avg <paste>.
- Least connections needs release() on every request, including failures
  (try/finally in the proxy). Otherwise counts drift and the strategy
  misjudges load.
- Ties rotate, so an idle system doesn't send everything to the first backend.
- Weighted (smooth, as in nginx) is for unequal servers. Weights are static:
  it can't react to a server that is slow right now.
- Still missing: none of these know a backend is dead (health checks, Step 7).