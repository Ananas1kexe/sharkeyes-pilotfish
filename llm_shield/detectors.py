
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Optional


@dataclass(frozen=True)
class Match:
    start: int
    end: int
    kind: str
    value: str
    priority: int



def luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def israeli_id_ok(number: str) -> bool:
    digits = re.sub(r"\D", "", number)
    if len(digits) != 9 or digits == "0" * 9:
        return False
    total = 0
    for i, ch in enumerate(digits):
        n = int(ch) * (1 if i % 2 == 0 else 2)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def iban_ok(value: str) -> bool:
    s = value.replace(" ", "").upper()
    if not 15 <= len(s) <= 34 or not s[:2].isalpha() or not s[2:4].isdigit():
        return False
    if not s.isalnum():
        return False
    rearranged = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1


def _intl_phone_ok(value: str) -> bool:
    return 8 <= len(re.sub(r"\D", "", value)) <= 15



class Detector:
    kind: str = ""
    priority: int = 0

    def find(self, text: str) -> Iterator[Match]:
        raise NotImplementedError


class RegexDetector(Detector):
    def __init__(
        self,
        kind: str,
        pattern: str,
        priority: int,
        group: int = 0,
        validate: Optional[Callable[[str], bool]] = None,
        flags: int = 0,
    ) -> None:
        self.kind = kind
        self.priority = priority
        self.group = group
        self.validate = validate
        self._re = re.compile(pattern, flags)

    def find(self, text: str) -> Iterator[Match]:
        for m in self._re.finditer(text):
            value = m.group(self.group)
            if not value:
                continue
            if self.validate and not self.validate(value):
                continue
            yield Match(m.start(self.group), m.end(self.group), self.kind, value, self.priority)


class IbanDetector(Detector):

    kind = "IBAN"

    def __init__(self, priority: int = 85) -> None:
        self.priority = priority
        self._re = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{3,4}){3,8}\b")

    def find(self, text: str) -> Iterator[Match]:
        for m in self._re.finditer(text):
            cand = m.group(0)
            while cand:
                if iban_ok(cand):
                    yield Match(m.start(), m.start() + len(cand), self.kind, cand, self.priority)
                    break
                cut = cand.rfind(" ")
                if cut == -1:
                    break
                cand = cand[:cut]



_SECRET = (
    r"(?<![A-Za-z0-9])(?:"
    r"sk-[A-Za-z0-9_-]{20,}"                      # OpenAI / Anthropic style keys
    r"|AKIA[0-9A-Z]{16}"                          # AWS access key id
    r"|gh[pousr]_[A-Za-z0-9]{36,}"                # GitHub tokens
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"              # Slack tokens
    r"|eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"  # JWT
    r")"
)
_PRIVATE_KEY = r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"

_IL_PHONE = (
    r"(?<![\w+])(?:\+972|972|0)[-\s]?(?:5\d|7\d|[23489])[-\s]?\d{3}[-\s]?\d{4}(?!\d)"
)
_INTL_PHONE = r"(?<![\w+])\+\d{1,3}[\s-]?\(?\d{1,4}\)?(?:[\s-]?\d{2,4}){2,4}(?!\d)"

_EN_NAME = (
    r"(?i:\b(?:my name is|name is|call me))\s+"
    r"([A-Z][a-z'’-]+(?:\s+[A-Z][a-z'’-]+){0,2})"
)
_HE_NAME = (
    r"(?:שמי(?:\s+הוא)?|קוראים\s+לי|שם\s+מלא:?)\s+"
    r"([\u05D0-\u05EA]{2,}(?:\s+(?!ו)[\u05D0-\u05EA]{2,})?)"
)
_RU_NAME = (
    r"(?i:\b(?:меня\s+зовут|моё\s+имя|мое\s+имя))\s+"
    r"([А-ЯЁ][а-яё-]+(?:\s+[А-ЯЁ][а-яё-]+)?)"
)


def default_detectors() -> list[Detector]:
    return [
        RegexDetector("SECRET", _PRIVATE_KEY, 100),
        RegexDetector("SECRET", _SECRET, 100),
        RegexDetector("EMAIL", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}", 90),
        IbanDetector(85),
        RegexDetector("CARD", r"(?<![\d-])[2-6](?:[ -]?\d){12,18}(?!\d)", 80, validate=luhn_ok),
        RegexDetector("PHONE", _IL_PHONE, 70),
        RegexDetector("PHONE", _INTL_PHONE, 65, validate=_intl_phone_ok),
        RegexDetector("IL_ID", r"(?<!\d)\d{9}(?!\d)", 60, validate=israeli_id_ok),
        RegexDetector(
            "IP",
            r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])",
            50,
        ),
        RegexDetector("NAME", _EN_NAME, 40, group=1),
        RegexDetector("NAME", _HE_NAME, 40, group=1),
        RegexDetector("NAME", _RU_NAME, 40, group=1),
    ]


def find_all(
    text: str,
    detectors: Iterable[Detector],
    kinds: Optional[set[str]] = None,
) -> list[Match]:
    candidates: list[Match] = []
    for d in detectors:
        if kinds is not None and d.kind not in kinds:
            continue
        candidates.extend(d.find(text))
    candidates.sort(key=lambda m: (-m.priority, -(m.end - m.start), m.start))
    taken: list[Match] = []
    for m in candidates:
        if any(m.start < t.end and t.start < m.end for t in taken):
            continue
        taken.append(m)
    taken.sort(key=lambda m: m.start)
    return taken
