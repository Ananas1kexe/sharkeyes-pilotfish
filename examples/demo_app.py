from __future__ import annotations

from typing import Any, AsyncIterator

from fastapi import Depends, FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm_shield import Shield, Session
from llm_shield.contrib_fastapi import install, session_dependency
from llm_shield.vault import TOKEN_RE

shield = Shield(on_injection="raise")
get_session = session_dependency(shield)

app = FastAPI(title="llm-shield demo")
install(app)

LLM_LOG: list[list[dict[str, Any]]] = []


def _fake_reply(messages: list[dict[str, Any]]) -> str:
    tokens = TOKEN_RE.findall(messages[-1]["content"])
    by_kind = {}
    for t in tokens:
        by_kind.setdefault(t.rsplit("_", 1)[0], f"[{t}]")
    name = by_kind.get("NAME", "")
    parts = [f"Hello{', ' + name if name else ''}!"]
    if "EMAIL" in by_kind:
        parts.append(f"I will send confirmation to {by_kind['EMAIL']}.")
    if "PHONE" in by_kind:
        parts.append(f"I will call you at {by_kind['PHONE']}.")
    if "IL_ID" in by_kind:
        parts.append(f"I verified document {by_kind['IL_ID']}.")
    return " ".join(parts)


async def fake_llm(messages: list[dict[str, Any]]) -> str:
    LLM_LOG.append(messages)
    return _fake_reply(messages)


async def fake_llm_stream(messages: list[dict[str, Any]]) -> AsyncIterator[str]:
    LLM_LOG.append(messages)
    reply = _fake_reply(messages)
    for i in range(0, len(reply), 4):
        yield reply[i : i + 4]


class ChatIn(BaseModel):
    message: str


def _messages(text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "You are a helpful support assistant."},
        {"role": "user", "content": text},
    ]


@app.post("/chat")
async def chat(body: ChatIn, session: Session = Depends(get_session)):
    safe = session.redact_messages(_messages(body.message))
    reply = await fake_llm(safe)
    return {
        "reply": session.restore(reply),
        "llm_saw": safe[-1]["content"],
        "summary": session.summary(),
    }


@app.post("/chat/stream")
async def chat_stream(body: ChatIn):
    session = shield.session()
    safe = session.redact_messages(_messages(body.message))

    async def body_iter():
        try:
            async for piece in session.restore_stream(fake_llm_stream(safe)):
                yield piece
        finally:
            session.vault.clear()

    return StreamingResponse(body_iter(), media_type="text/plain; charset=utf-8")