import asyncio
import os
import time
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from lb import metrics
from lb.forward import forward
from lb.health import HealthTracker, health_loop
from lb.strategies import build_strategy

NAMES = {                       # short names, used as metric labels
    "http://127.0.0.1:9001": "A",
    "http://127.0.0.1:9002": "B",
    "http://127.0.0.1:9003": "C",
}
BACKENDS = list(NAMES)
strategy = build_strategy(BACKENDS)
tracker = HealthTracker(BACKENDS)

MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "3"))             # total tries per request
ATTEMPT_TIMEOUT = float(os.getenv("ATTEMPT_TIMEOUT", "2.0"))   # seconds to wait for a reply
CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "0.5"))   # seconds to wait to connect
RETRY_UNSAFE = os.getenv("RETRY_UNSAFE", "0") == "1"           # DANGEROUS: demo only
TIMEOUT = httpx.Timeout(ATTEMPT_TIMEOUT, connect=CONNECT_TIMEOUT)

# Headers that describe one network hop and must not be copied across
HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


def record_transition(backend, ok):
    metrics.TRANSITIONS.labels(NAMES[backend], "up" if ok else "down").inc()


@asynccontextmanager
async def lifespan(app):
    app.state.client = httpx.AsyncClient()
    checker = asyncio.create_task(
        health_loop(app.state.client, strategy, tracker, on_change=record_transition))
    yield
    checker.cancel()
    with suppress(asyncio.CancelledError):
        await checker
    await app.state.client.aclose()


app = FastAPI(lifespan=lifespan)


# The two routes below must be defined before the catch-all route, or the
# catch-all would forward them to a backend instead.
@app.get("/_lb/status")
async def status():
    return {
        "healthy": {b: (b in strategy.healthy) for b in BACKENDS},
        "in_flight": getattr(strategy, "active", None),
        "max_attempts": MAX_ATTEMPTS,
        "attempt_timeout": ATTEMPT_TIMEOUT,
        "retry_unsafe": RETRY_UNSAFE,
    }


@app.get("/metrics")
async def metrics_endpoint():
    # Gauges describe "right now", so refresh them at the moment of the scrape
    active = getattr(strategy, "active", None)
    for b in BACKENDS:
        metrics.BACKEND_UP.labels(NAMES[b]).set(1 if b in strategy.healthy else 0)
        if active is not None:
            metrics.IN_FLIGHT.labels(NAMES[b]).set(active[b])
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(path: str, request: Request):
    start = time.perf_counter()
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
    headers["x-forwarded-for"] = request.client.host

    result = await forward(
        app.state.client, strategy, request.method, path,
        request.query_params, body, headers,
        max_attempts=MAX_ATTEMPTS, timeout=TIMEOUT, retry_unsafe=RETRY_UNSAFE,
    )

    # record what happened on every attempt, then what the client received
    for backend, outcome in result.attempt_log:
        metrics.ATTEMPTS.labels(NAMES[backend], outcome).inc()
    if result.attempts > 1:
        metrics.RETRIED.inc()

    if result.upstream is not None:
        upstream = result.upstream
        # httpx already decoded the body, so drop headers that describe the encoded one
        response_headers = {
            k: v for k, v in upstream.headers.items()
            if k.lower() not in HOP_HEADERS and k.lower() != "content-encoding"
        }
        response_headers["x-backend"] = result.backend
        response_headers["x-attempts"] = str(result.attempts)
        response = Response(upstream.content, status_code=upstream.status_code,
                            headers=response_headers)
    elif not result.tried:
        response = JSONResponse({"error": "no healthy backends"}, status_code=503)
    else:
        # 504 = the backend took too long, 502 = the backend could not be reached or broke
        code = 504 if isinstance(result.error, httpx.TimeoutException) else 502
        response = JSONResponse(
            {"error": "gateway timeout" if code == 504 else "bad gateway",
             "attempts": result.attempts, "tried": result.tried},
            status_code=code,
            headers={"x-attempts": str(result.attempts)},
        )

    metrics.REQUESTS.labels(str(response.status_code)).inc()
    metrics.DURATION.observe(time.perf_counter() - start)
    return response