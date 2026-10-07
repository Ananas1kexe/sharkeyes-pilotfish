
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from core.config import VERSION

router = APIRouter()

async def health_check(request: Request):
    return JSONResponse(
        content={
            "status": "ok",
            "version": VERSION,
        },
        status_code=status.HTTP_200_OK,
    )