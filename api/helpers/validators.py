import re

#english+hebrew patter
NAME_PATTERN = r"^[a-zA-Zа-яА-ЯёЁ\u0590-\u05FF]+([ '-][a-zA-Zа-яА-ЯёЁ\u0590-\u05FF]+)*$"
STOP_WORDS = {"mail", "card", "phone", "email", "name", "text"}
def name_ok(s: str) -> bool:
    word = s.lower()
    if word in STOP_WORDS:
        return False
    name = s.strip()

    if not 2 <= len(name) <= 50:
        return False

    return bool(re.fullmatch(NAME_PATTERN, name))

def phone_ok(s: str) -> bool:
    return 9 <= len(re.sub(r"\D", "", s)) <= 15

def luhn_ok(s: str) -> bool:
    digits = [int(c) for c in re.sub(r"\D", "", s)]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, n in enumerate(reversed(digits)):
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0
