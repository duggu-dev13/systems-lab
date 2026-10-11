import os
import asyncio
from fastapi import FastAPI

app = FastAPI()
NAME = os.getenv("SERVER_NAME", "backend")

# Each backend can work on this many requests at once. Extra ones wait.
CAPACITY = int(os.getenv("CAPACITY", "2"))
slots = asyncio.Semaphore(CAPACITY)

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


@app.get("/health")
async def health():
    return {"status": "ok"}            # deliberately outside the semaphore