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

## Timeouts and retries
- Each attempt has its own timeout: 0.5s to connect, 2s for a reply.
  Too short = healthy-but-slow servers get abandoned. Too long = clients wait.
- Retries go to a DIFFERENT backend each time, max 3 attempts total.
- Whether a retry is safe depends on how the attempt failed:
  - Connect failure: request never arrived, safe for every method.
  - Read timeout / reset: backend may have done the work. Only retry
    idempotent methods (GET, HEAD, OPTIONS, PUT, DELETE), never POST/PATCH.
- Experiment 1: killing B during traffic, errors before retries: <paste>,
  after retries: <paste>.
- Experiment 2 (RETRY_UNSAFE=1): one POST /book created <paste> bookings
  and the client still got a 504.
- Experiment 3 (safe default): one booking, but the client still got 504.
  The proxy cannot know whether the booking happened. The real fix is an
  idempotency key from the client (lab 6).
- Status codes: 502 = unreachable/broken, 504 = too slow, 503 = nothing healthy.
- Retries advance the round-robin counter, which can slightly skew the
  distribution while a backend is failing. Acceptable for now.
- Not built: backoff/jitter, a retry budget (retries amplify load in an
  overload), retrying on 5xx responses, and passive health checks (marking a
  backend down after real failed requests, not only the periodic ones).

## Metrics for the load balancer
- Apps run on the host, Prometheus + Grafana in Docker (same as lab 1).
  Apps need --host 0.0.0.0 so the containers can reach them.
- Two views of backend health on purpose: lb_backend_up (the balancer's
  belief) vs up{job="backends"} (Prometheus's scrape). The gap between them
  is the detection delay.
- Per-attempt outcomes (ok / connect_failed / timeout / error) recorded per
  backend, so a failing backend is visible even when clients see no errors
  (retries hide them).
- Gauges refreshed at scrape time, because they describe "now".
- Backend path label comes from the matched route, not the raw URL, to keep
  label cardinality bounded.
- /metrics defined before the catch-all route, or it would be proxied.