import re

from api.helpers.utils import luhn_ok, phone_ok

VERSION = "0.0.1"
SESSION_TTL = 900
SESSIONS: dict[str, dict] = {}
SYSTEM_PROMPT = (
    "Some values in this conversation were replaced by placeholders such as "
    "[EMAIL_1] or [PHONE_2]. Treat them as opaque and reuse them verbatim when needed."
)


PLACEHOLDER_RE = re.compile(r"\[[A-Z]+_\d+\]")


DETECTORS = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), None),
    ("CARD", re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"), luhn_ok),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b"), None),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), None),
    ("PHONE", re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,16}\d(?!\w)"), phone_ok),
]
