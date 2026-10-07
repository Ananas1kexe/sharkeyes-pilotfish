from fastapi import APIRouter, Request

from api.services.handlers.meta.health import health_check
from core.limiter import limiter

router = APIRouter()

@router.api_route("/health", methods=["GET", "HEAD"])
@limiter.limit("30/minute")
async def api_health_endpoint(request: Request):
    return await health_check(request)