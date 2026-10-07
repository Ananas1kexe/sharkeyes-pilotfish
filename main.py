from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI

from endpoints import health, sanitizer

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=4.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
    )
    yield



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
app.include_router(health.router, prefix="")
