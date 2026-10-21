from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Iterable
from typing import (
    Any,
    Callable,
    Optional,
)

from .detectors import Detector, default_detectors, find_all
from .injection import InjectionReport, scan_injection
from .stream import restore_aiter, restore_iter
from .vault import Vault


class InjectionBlocked(Exception):

    def __init__(self, report: InjectionReport) -> None:
        super().__init__(f"possible prompt injection (score={report.score}, level={report.level})")
        self.report = report


class Shield:
    def __init__(
        self,
        detectors: Optional[list[Detector]] = None,
        kinds: Optional[Iterable[str]] = None,
        on_injection: str = "flag",
        injection_threshold: float = 0.7,
    ) -> None:
        if on_injection not in {"flag", "raise"}:
            raise ValueError('on_injection must be "flag" or "raise"')
        self.detectors = detectors if detectors is not None else default_detectors()
        self.kinds = set(kinds) if kinds is not None else None
        self.on_injection = on_injection
        self.injection_threshold = injection_threshold

    def session(self) -> Session:
        return Session(self)

    def wrap(
        self, llm: Callable[..., Awaitable[str]]
    ) -> Callable[..., Awaitable[str]]:

        async def guarded(messages: list[dict[str, Any]], **kwargs: Any) -> str:
            with self.session() as s:
                reply = await llm(s.redact_messages(messages), **kwargs)
                return s.restore(reply)

        return guarded


class Session:

    def __init__(self, shield: Shield) -> None:
        self.shield = shield
        self.vault = Vault()
        self.injections: list[InjectionReport] = []

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *exc: object) -> None:
        self.vault.clear()

    def redact(self, text: str) -> str:
        out: list[str] = []
        last = 0
        for m in find_all(text, self.shield.detectors, self.shield.kinds):
            out.append(text[last : m.start])
            out.append(self.vault.tokenize(m.kind, m.value))
            last = m.end
        out.append(text[last:])
        return "".join(out)

    def check_injection(self, text: str) -> InjectionReport:
        report = scan_injection(text)
        if report:
            self.injections.append(report)
        if self.shield.on_injection == "raise" and report.score >= self.shield.injection_threshold:
            raise InjectionBlocked(report)
        return report

    def redact_messages(
        self,
        messages: list[dict[str, Any]],
        scan_roles: tuple[str, ...] = ("user", "tool", "function"),
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for msg in messages:
            new = dict(msg)
            scan = msg.get("role", "user") in scan_roles
            content = msg.get("content")
            if isinstance(content, str):
                new["content"] = self._process(content, scan)
            elif isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                        p = dict(part)
                        p["text"] = self._process(part["text"], scan)
                        parts.append(p)
                    else:
                        parts.append(part)
                new["content"] = parts
            out.append(new)
        return out

    def _process(self, text: str, scan: bool) -> str:
        if scan:
            self.check_injection(text)
        return self.redact(text)

    def restore(self, text: str) -> str:
        return self.vault.restore(text)

    def restore_iter(self, chunks: Iterable[str]):
        return restore_iter(self.vault, chunks)

    def restore_stream(self, chunks: AsyncIterable[str]) -> AsyncIterator[str]:
        return restore_aiter(self.vault, chunks)
    
    def found_kinds(self) -> list[str]:
        return sorted(self.vault.counts())
    
    def summary(self) -> dict[str, Any]:
        worst = max(self.injections, key=lambda r: r.score, default=None)
        return {
            "redacted_distinct": self.vault.counts(),
            "injection": {
                "max_score": worst.score if worst else 0.0,
                "level": worst.level if worst else "none",
                "signals": sorted({f.name for r in self.injections for f in r.findings}),
            },
        }
