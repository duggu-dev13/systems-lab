import os
import asyncio
from fastapi import FastAPI

app = FastAPI()
NAME = os.getenv("SERVER_NAME", "backend")

@app.get("/api/ping")
def ping():
    return {"served_by": NAME}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/slow")
async def slow(delay: float = 1.0):
    await asyncio.sleep(delay)
    return {"served_by": NAME, "delay": delay}