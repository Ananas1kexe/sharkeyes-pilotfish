from typing import Literal

from pydantic import BaseModel, Field


class RedactIn(BaseModel):
    text: str = Field(max_length=100_000)
    session_id: str | None = None


class RestoreIn(BaseModel):
    text: str = Field(max_length=100_000)
    session_id: str 


class Msg(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatIn(BaseModel):
    model: str = "unknown"
    company: str = "unknown"
    message: list[Msg]
    max_tokens: int = Field(1024, le=8192)

