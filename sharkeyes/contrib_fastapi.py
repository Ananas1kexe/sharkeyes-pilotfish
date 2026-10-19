from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .shield import InjectionBlocked, Session, Shield


def session_dependency(shield: Shield) -> Callable[[], Session]:

    def dep():
        with shield.session() as s:
            yield s

    return dep


def install(app: FastAPI) -> None:

    async def handler(request: Request, exc: InjectionBlocked) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": "prompt_injection_suspected",
                "score": round(exc.report.score, 2),
                "signals": [f.name for f in exc.report.findings],
            },
        )

    app.add_exception_handler(InjectionBlocked, handler)
