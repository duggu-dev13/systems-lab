import os
import asyncio
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

app = FastAPI()
NAME = os.getenv("SERVER_NAME", "backend")

# Each backend can work on this many requests at once. Extra ones wait.
CAPACITY = int(os.getenv("CAPACITY", "2"))
slots = asyncio.Semaphore(CAPACITY)

REQUESTS = Counter("backend_requests_total", "Requests handled by this backend",
                   ["server", "path"])


@app.middleware("http")
async def count_requests(request: Request, call_next):
    response = await call_next(request)
    route = request.scope.get("route")           # the matched route, e.g. "/api/ping"
    path = route.path if route else "other"      # avoids one label value per random URL
    if path not in ("/metrics", "/health"):
        REQUESTS.labels(NAME, path).inc()
    return response


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


bookings = []          # pretend database: one entry per booking made on THIS backend


@app.get("/api/ping")
async def ping():
    async with slots:
        await asyncio.sleep(0.05)      # 50 ms of pretend work
        return {"served_by": NAME}


@app.get("/slow")
async def slow(delay: float = 1.0):
    async with slots:
        await asyncio.sleep(delay)
        return {"served_by": NAME, "delay": delay}


@app.post("/book")
async def book(delay: float = 0.0):
    async with slots:
        bookings.append(len(bookings) + 1)   # the booking is saved immediately...
        await asyncio.sleep(delay)           # ...but the reply can be slow
        return {"served_by": NAME, "booking_no": len(bookings)}


@app.get("/bookings")
async def list_bookings():
    return {"served_by": NAME, "count": len(bookings)}


@app.post("/_admin/die")
async def die():
    # Crash this process 0.1s after replying, simulating a server failure.
    # Lab only: never expose an endpoint like this in a real system.
    asyncio.get_running_loop().call_later(0.1, os._exit, 1)
    return {"dying": NAME}


@app.get("/health")
async def health():
    return {"status": "ok"}            # deliberately outside the semaphore