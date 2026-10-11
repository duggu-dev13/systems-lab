import os
import asyncio
from fastapi import FastAPI

app = FastAPI()
NAME = os.getenv("SERVER_NAME", "backend")

# Each backend can work on this many requests at once. Extra ones wait.
CAPACITY = int(os.getenv("CAPACITY", "2"))
slots = asyncio.Semaphore(CAPACITY)

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

@app.get("/health")
async def health():
    return {"status": "ok"}            # deliberately outside the semaphore