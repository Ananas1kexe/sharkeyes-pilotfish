import secrets
import time

import httpx
from fastapi import HTTPException

from api.helpers.utils import purge_expired
from api.services.logic.general import redact, restore
from core.config import SESSION_TTL, SESSIONS, SYSTEM_PROMPT
from repository.schemas.schemas import RedactIn, RestoreIn


async def chat_handlers(body, x_provider_key):
    mapping: dict[str, str] = {}  
    safe_messages = [{"role": m.role, "content": redact(m.content, mapping)} for m in body.messages]
 
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": x_provider_key, "anthropic-version": "2023-06-01"},
            json={
                "model": body.model,
                "max_tokens": body.max_tokens,
                "system": SYSTEM_PROMPT,
                "messages": safe_messages,
            },
        )
    if r.status_code != 200:
        raise HTTPException(502, f"upstream returned {r.status_code}")
 
    text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
    return {"text": restore(text, mapping), "entities_redacted": len(mapping)}
 

async def redact_endpoint_handlers(body: RedactIn):
    purge_expired()
    if body.session_id:
        session = SESSIONS.get(body.session_id)
        if not session:
            raise HTTPException(404, "session not found or expired")
        sid = body.session_id
    else:
        sid = secrets.token_urlsafe(16)
        session = SESSIONS[sid] = {"map": {}, "exp": 0}
    clean = redact(body.text, session["map"])
    session["exp"] = time.time() + SESSION_TTL
    return {"session_id": sid, "text": clean, "entities": len(session["map"])}
 


def restore_endpoint_handlers(body: RestoreIn):
    purge_expired()
    session = SESSIONS.get(body.session_id)
    if not session:
        raise HTTPException(404, "session not found or expired")
    return {"text": restore(body.text, session["map"])}
