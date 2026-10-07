import asyncio
import re
import secrets

import structlog
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.config import MAX_FILE_SIZE, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN
from core.logger import logger
from core.setup import DEBUG

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_STATIC_HEADERS = [
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains; preload"),
    (b"x-xss-protection", b"1; mode=block"),
    (b"x-content-type-options", b"nosniff"),
    (b"x-robots-tag", b"noindex, nofollow"),
]


def _clean_id(value: str | None) -> str:
    if value and _ID_RE.match(value):
        return value
    return secrets.token_hex(8)


class SkyHeadersMiddleware:

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        sky_id = _clean_id(headers.get("x-sky-id"))
        state = scope.setdefault("state", {})
        state["skyid"] = sky_id
        log_context = {"sky_id": sky_id}

        extra = [*_STATIC_HEADERS, (b"x-sky-id", sky_id.encode())]
        if DEBUG:
            debug_id = _clean_id(headers.get("x-sky-debug"))
            state["debug_id"] = debug_id
            log_context["debug_id"] = debug_id
            extra.append((b"x-sky-debug", debug_id.encode()))

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**log_context)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [*message.get("headers", []), *extra]
            await send(message)

        await self.app(scope, receive, send_wrapper)


class LimitBodyMiddleware:

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            raw = Headers(scope=scope).get("content-length")
            if raw:
                try:
                    too_big = int(raw) > MAX_FILE_SIZE
                except ValueError:
                    too_big = False
                if too_big:
                    response = JSONResponse({"detail": "Payload too large"}, status_code=413)
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)


_alert_tasks: set[asyncio.Task] = set()


async def _send_telegram_alert(client, error_trace: str) -> None:
    try:
        text = f"<b>[500 ERROR]</b>\n\n<code>{error_trace}</code>"
        await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
        )
    except Exception as err:  # noqa: BLE001
        logger.error(f"Telegram alert delivery failed: {err}")


class HandleErrorMiddleware:

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as err:
            logger.error(err, exc_info=True)
            if started:
                raise 
            import traceback

            trace = traceback.format_exc()[-1000:]
            client = scope["app"].state.http_client
            task = asyncio.create_task(_send_telegram_alert(client, trace))
            _alert_tasks.add(task)
            task.add_done_callback(_alert_tasks.discard)

            response = JSONResponse(
                {"status": "error", "message": "Internal Server Error"}, status_code=500
            )
            await response(scope, receive, send)