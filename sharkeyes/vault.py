
from __future__ import annotations

import re

from .core.config import TOKEN_RE


def _norm(kind: str, value: str) -> str:
    v = value.strip()
    if kind == "EMAIL":
        return v.lower()
    if kind == "PHONE":
        digits = re.sub(r"\D", "", v)
        if digits.startswith("972"):
            digits = "0" + digits[3:]
        return digits
    if kind in {"CARD", "IL_ID", "IBAN"}:
        return re.sub(r"[^0-9A-Za-z]", "", v).upper()
    if kind == "NAME":
        return " ".join(v.split()).lower()
    return v
MAX_TOKEN_LEN = 40
class Vault:
    def __init__(self) -> None:
        self._token_by_key: dict[tuple[str, str], str] = {}
        self._value_by_token: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    def tokenize(self, kind: str, value: str) -> str:
        key = (kind, _norm(kind, value))
        token = self._token_by_key.get(key)
        if token is None:
            n = self._counts.get(kind, 0) + 1
            self._counts[kind] = n
            token = f"[{kind}_{n}]"
            self._token_by_key[key] = token
            self._value_by_token[token] = value
        return token

    def restore(self, text: str) -> str:

        def sub(m: re.Match) -> str:
            return self._value_by_token.get(f"[{m.group(1)}]", m.group(0))

        return TOKEN_RE.sub(sub, text)

    def counts(self) -> dict[str, int]:
        return dict(self._counts)

    def clear(self) -> None:
        self._token_by_key.clear()
        self._value_by_token.clear()
        self._counts.clear()

    def __len__(self) -> int:
        return len(self._value_by_token)

    def __repr__(self) -> str:
        return f"Vault(<{len(self)} values hidden>)"
