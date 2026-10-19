
from __future__ import annotations

from typing import AsyncIterable, AsyncIterator, Iterable, Iterator

from .vault import MAX_TOKEN_LEN, Vault


class StreamRestorer:
    def __init__(self, vault: Vault) -> None:
        self._vault = vault
        self._buf = ""

    @staticmethod
    def _ready_upto(buf: str) -> int:
        i = buf.rfind("[")
        if i == -1 or "]" in buf[i:] or len(buf) - i > MAX_TOKEN_LEN:
            return len(buf)
        return i

    def feed(self, chunk: str) -> str:
        self._buf += chunk
        cut = self._ready_upto(self._buf)
        ready, self._buf = self._buf[:cut], self._buf[cut:]
        return self._vault.restore(ready)

    def flush(self) -> str:
        out = self._vault.restore(self._buf)
        self._buf = ""
        return out


def restore_iter(vault: Vault, chunks: Iterable[str]) -> Iterator[str]:
    r = StreamRestorer(vault)
    for c in chunks:
        out = r.feed(c)
        if out:
            yield out
    tail = r.flush()
    if tail:
        yield tail


async def restore_aiter(vault: Vault, chunks: AsyncIterable[str]) -> AsyncIterator[str]:
    r = StreamRestorer(vault)
    async for c in chunks:
        out = r.feed(c)
        if out:
            yield out
    tail = r.flush()
    if tail:
        yield tail
