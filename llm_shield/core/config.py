import re


_HIDDEN = re.compile("[​-‍⁠﻿‪-‮⁦-⁩]")
_NIQQUD = re.compile("[֑-ׇ]")


TOKEN_RE = re.compile(r"\[\s*([A-Z][A-Z_]*_\d+)\s*\]")
MAX_TOKEN_LEN = 40

_BASE64_BLOB = re.compile(r"[A-Za-z0-9+/]{120,}={0,2}")

_FLAGS = re.IGNORECASE | re.MULTILINE

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
