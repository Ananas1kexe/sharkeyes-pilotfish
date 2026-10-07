
import re
import time

from core.config import SESSIONS


def phone_ok(s: str) -> bool:
    return 9 <= len(re.sub(r"\D", "", s)) <= 15

def luhn_ok(s: str) -> bool:
    digist = [int(c) for c in re.sub(r"\D", "", s)]
    if not 13 <= len(digist) <= 19:
        return False
    total = 0
    for i, n in enumerate(reversed(digist)):
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0

def purge_expired() -> None:
    now = time.time()
    for sid in [s for s, v in SESSIONS.items() if v["exp"] < now]:
        del SESSIONS[sid]
