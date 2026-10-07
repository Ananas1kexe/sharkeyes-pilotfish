from fastapi import APIRouter, Header

from api.services.handlers.handlers import (
    chat_handlers,
    redact_endpoint_handlers,
    restore_endpoint_handlers,
)
from repository.schemas.schemas import ChatIn, RedactIn, RestoreIn

router = APIRouter()

@router.post("/v1/chat")
async def chat(body: ChatIn, x_provider_key: str = Header(...)):
    return await chat_handlers(body, x_provider_key)


@router.post("/v1/redact")
async def redact_endpoint(body: RedactIn):
    return await redact_endpoint_handlers(body)


@router.post("/v1/restore")
async def restore_endpoint(body: RestoreIn):
    return await restore_endpoint_handlers(body)