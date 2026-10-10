import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app import metrics
from app.config import ALGORITHM, build_limiter

app = FastAPI()
limiter = build_limiter()

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    # Prometheus must never be rate limited, or it can't scrape us
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    key = request.client.host

    t0 = time.perf_counter()
    decision = limiter.check(key)
    metrics.DECISION_SECONDS.labels(ALGORITHM).observe(time.perf_counter() - t0)

    if not decision.allowed:
        metrics.REQUESTS.labels(ALGORITHM, "rejected").inc()
        response = JSONResponse(
            {"error": "too many requests"},
            status_code=429,
            headers={"Retry-After": str(int(decision.retry_after) + 1)},
        )
    else:
        metrics.REQUESTS.labels(ALGORITHM, "allowed").inc()
        response = await call_next(request)

    metrics.HTTP_RESPONSES.labels(str(response.status_code)).inc()
    metrics.HTTP_DURATION.observe(time.perf_counter() - start)
    return response

@app.get("/api/ping")
def ping():
    return {"message": "pong"}

@app.get("/metrics")
def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)