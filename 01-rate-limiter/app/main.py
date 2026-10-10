from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.limiters.fixed_window import FixedWindowLimiter
from app.limiters.sliding_log import SlidingLogLimiter
from app.limiters.sliding_counter import SlidingCounterLimiter
app = FastAPI()

limiter = FixedWindowLimiter(limit=5, window_seconds=10)
limiter = SlidingLogLimiter(limit=5, window_seconds=10)
limiter = SlidingCounterLimiter(limit=5, window_seconds=10)

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    key = request.client.host            # identify the client by IP
    decision = limiter.check(key)
    if not decision.allowed:
        return JSONResponse(
            {"error": "too many requests"},
            status_code=429,
            headers={"Retry-After": str(int(decision.retry_after) + 1)},
        )
    return await call_next(request)

@app.get("/api/ping")
def ping():
    return {"message": "pong"}