import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from lb.strategies import build_strategy

BACKENDS = [
    "http://127.0.0.1:9001",
    "http://127.0.0.1:9002",
    "http://127.0.0.1:9003",
]

strategy = build_strategy(BACKENDS)
# strategy = RoundRobin(BACKENDS)


# Headers that describe one network hop and must not be copied across
HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}

@asynccontextmanager
async def lifespan(app):
    app.state.client = httpx.AsyncClient(timeout=10.0)
    yield
    await app.state.client.aclose()

app = FastAPI(lifespan=lifespan)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(path: str, request: Request):
    backend = strategy.pick()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_HEADERS}
    headers["x-forwarded-for"] = request.client.host

    try:
        upstream = await app.state.client.request(
            request.method,
            f"{backend}/{path}",
            params=request.query_params,
            content=await request.body(),
            headers=headers,
        )
    except httpx.HTTPError:
        return JSONResponse({"error": "bad gateway", "backend": backend}, status_code=502)
    finally:
        strategy.release(backend)

    # httpx already decoded the body, so drop headers that describe the encoded one
    response_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in HOP_HEADERS and k.lower() != "content-encoding"
    }
    response_headers["x-backend"] = backend
    return Response(upstream.content, status_code=upstream.status_code, headers=response_headers)