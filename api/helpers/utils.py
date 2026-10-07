
import time

from core.config import SESSIONS


def purge_expired() -> None:
    now = time.time()
    for sid in [s for s, v in SESSIONS.items() if v["exp"] < now]:
        del SESSIONS[sid]
