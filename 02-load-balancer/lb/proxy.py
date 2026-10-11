import asyncio
import os
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from lb.forward import forward
from lb.health import HealthTracker, health_loop
from lb.strategies import build_strategy

BACKENDS = [
    "http://127.0.0.1:9001",
    "http://127.0.0.1:9002",
    "http://127.0.0.1:9003",
]
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


@asynccontextmanager
async def lifespan(app):
    app.state.client = httpx.AsyncClient()
    checker = asyncio.create_task(health_loop(app.state.client, strategy, tracker))
    yield
    checker.cancel()
    with suppress(asyncio.CancelledError):
        await checker
    await app.state.client.aclose()


app = FastAPI(lifespan=lifespan)


# Must be defined before the catch-all route below
@app.get("/_lb/status")
async def status():
    return {
        "healthy": {b: (b in strategy.healthy) for b in BACKENDS},
        "in_flight": getattr(strategy, "active", None),
        "max_attempts": MAX_ATTEMPTS,
        "attempt_timeout": ATTEMPT_TIMEOUT,
        "retry_unsafe": RETRY_UNSAFE,
    }


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(path: str, request: Request):
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
    headers["x-forwarded-for"] = request.client.host

    result = await forward(
        app.state.client, strategy, request.method, path,
        request.query_params, body, headers,
        max_attempts=MAX_ATTEMPTS, timeout=TIMEOUT, retry_unsafe=RETRY_UNSAFE,
    )

    if result.upstream is not None:
        upstream = result.upstream
        # httpx already decoded the body, so drop headers that describe the encoded one
        response_headers = {
            k: v for k, v in upstream.headers.items()
            if k.lower() not in HOP_HEADERS and k.lower() != "content-encoding"
        }
        response_headers["x-backend"] = result.backend
        response_headers["x-attempts"] = str(result.attempts)
        return Response(upstream.content, status_code=upstream.status_code, headers=response_headers)

    if not result.tried:
        return JSONResponse({"error": "no healthy backends"}, status_code=503)

    # 504 = the backend took too long, 502 = the backend could not be reached or broke
    code = 504 if isinstance(result.error, httpx.TimeoutException) else 502
    return JSONResponse(
        {"error": "gateway timeout" if code == 504 else "bad gateway",
         "attempts": result.attempts, "tried": result.tried},
        status_code=code,
        headers={"x-attempts": str(result.attempts)},
    )