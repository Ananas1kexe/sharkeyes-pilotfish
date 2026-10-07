from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from endpoints import sanitizer


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=4.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
    )



app = FastAPI(
    debug=False,
    lifespan=lifespan,
    title="SharkEyes API Privacy Proxy For LLM",
    openapi_url=None, 
    docs_url=None, 
    redoc_url=None,
    terms_of_service="https://sharkeyes.dev/terms",
)

app.include_router(sanitizer.router, prefix="")
