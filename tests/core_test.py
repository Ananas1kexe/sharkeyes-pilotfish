import random
import string
import time

import pytest

from api.helpers.validators import luhn_ok, phone_ok
from api.services.logic.general import find_spans, redact, restore


def labels(text):
    return [label for _, _, label in find_spans(text)]


@pytest.mark.parametrize(
    "text, label",
    [
        ("anna@corp.io", "EMAIL"),
        ("first.last+tag@sub.example.co.uk", "EMAIL"),
        ("4111 1111 1111 1111", "CARD"),
        ("4111-1111-1111-1111", "CARD"),
        ("4111111111111111", "CARD"),
        ("5555 5555 5555 4444", "CARD"),
        ("3782 822463 10005", "CARD"),  
        ("IL62 0108 0000 0009 9999 999", "IBAN"),
        ("GB82 WEST 1234 5698 7654 32", "IBAN"),
        ("DE89 3704 0044 0532 0130 00", "IBAN"),
        ("192.168.1.10", "IP"),
        ("8.8.8.8", "IP"),
        ("+972 54-123-4567", "PHONE"),
        ("+1 (415) 555-2671", "PHONE"),
        ("+44 20 7946 0958", "PHONE"),
        ("054-1234567", "PHONE"),
    ],
)
def test_detects_each_type(text, label):
    assert labels(text) == [label]
    mapping = {}
    assert redact(text, mapping) == f"[{label}_1]"
    assert mapping == {f"[{label}_1]": text}


def test_detects_pii_inside_sentence():
    text = "Hi, write to anna@corp.io today."
    mapping = {}
    assert redact(text, mapping) == "Hi, write to [EMAIL_1] today."


@pytest.mark.parametrize(
    "text",
    [
        "2024-01-15",
        "Date 2024-01-15 and 15.01.2024",
        "1234 5678 9012 3456",  
        "Hello, world!",
        "",
        "a@b", 
        "version 3.14",
        "call me at 12345",  
    ],
)
def test_ignores_non_pii(text):
    mapping = {}
    assert redact(text, mapping) == text
    assert mapping == {}


def test_invalid_luhn_card_is_not_cut_into_phone():
    text = "number 1234 5678 9012 3456."
    assert redact(text, {}) == text


def test_ip_wins_over_phone():
    assert labels("192.168.1.10") == ["IP"]


def test_valid_card_wins_over_phone():
    assert labels("4111 1111 1111 1111") == ["CARD"]


def test_same_value_same_placeholder():
    mapping = {}
    assert redact("a@b.io and a@b.io", mapping) == "[EMAIL_1] and [EMAIL_1]"
    assert len(mapping) == 1


def test_different_values_get_incrementing_numbers():
    mapping = {}
    assert redact("a@b.io, c@d.io, e@f.io", mapping) == "[EMAIL_1], [EMAIL_2], [EMAIL_3]"


def test_counters_are_per_label():
    mapping = {}
    clean = redact("a@b.io 8.8.8.8 c@d.io 1.1.1.1", mapping)
    assert clean == "[EMAIL_1] [IP_1] [EMAIL_2] [IP_2]"


def test_mapping_is_reused_across_calls():
    mapping = {}
    first = redact("Mail a@b.io", mapping)
    second = redact("Again a@b.io and new c@d.io", mapping)
    assert first == "Mail [EMAIL_1]"
    assert second == "Again [EMAIL_1] and new [EMAIL_2]"


def test_no_pii_leaves_mapping_empty():
    mapping = {}
    assert redact("Nothing to see here", mapping) == "Nothing to see here"
    assert mapping == {}


def test_restore_replaces_known_placeholders():
    assert restore("Sent to [EMAIL_1]", {"[EMAIL_1]": "a@b.io"}) == "Sent to a@b.io"


def test_restore_leaves_unknown_placeholders():
    assert restore("see [EMAIL_9]", {}) == "see [EMAIL_9]"


def test_restore_handles_repeated_placeholder():
    assert restore("[EMAIL_1] and [EMAIL_1]", {"[EMAIL_1]": "a@b.io"}) == "a@b.io and a@b.io"


def test_restore_does_not_expand_values_recursively():
    mapping = {"[EMAIL_1]": "[EMAIL_2]", "[EMAIL_2]": "secret"}
    assert restore("[EMAIL_1]", mapping) == "[EMAIL_2]"


def test_roundtrip_mixed_text():
    text = (
        "Write to anna@corp.io or call +972 54-123-4567. "
        "Card 4111 1111 1111 1111, IBAN IL62 0108 0000 0009 9999 999, "
        "server 192.168.1.10, date 2024-01-15."
    )
    mapping = {}
    clean = redact(text, mapping)
    for secret in ["anna@corp.io", "54-123-4567", "4111", "IL62", "192.168"]:
        assert secret not in clean
    assert "2024-01-15" in clean 
    assert restore(clean, mapping) == text


def test_roundtrip_with_unicode_around_pii():
    text = "Привет! Напиши на anna@corp.io — спасибо. שלום, התקשר ל-+972 54-123-4567."
    mapping = {}
    clean = redact(text, mapping)
    assert "Привет" in clean and "שלום" in clean
    assert "anna@corp.io" not in clean
    assert restore(clean, mapping) == text


def test_roundtrip_random_texts():
    rnd = random.Random(1234)
    pieces = ["a@b.io", "8.8.8.8", "4111 1111 1111 1111", "+972 54-123-4567", "hello", "мир", "2024-01-15", " ", ". "]
    for _ in range(200):
        text = "".join(rnd.choice(pieces) + " " for _ in range(rnd.randint(1, 12)))
        mapping = {}
        assert restore(redact(text, mapping), mapping) == text


def test_spans_never_overlap_and_are_sorted():
    text = "a@b.io 192.168.1.10 +972 54-123-4567 4111 1111 1111 1111 8.8.8.8"
    spans = find_spans(text)
    assert spans == sorted(spans)
    for (_, e1, _), (s2, _, _) in zip(spans, spans[1:]):
        assert e1 <= s2


@pytest.mark.parametrize("number", ["4111111111111111", "5555555555554444", "378282246310005", "6011111111111117"])
def test_luhn_accepts_valid_test_cards(number):
    assert luhn_ok(number)


@pytest.mark.parametrize("number", ["4111111111111112", "1234567890123456", "123", ""])
def test_luhn_rejects_invalid(number):
    assert not luhn_ok(number)


@pytest.mark.parametrize("value, ok", [("054-1234567", True), ("2024-01-15", False), ("+972 54-123-4567", True), ("1" * 16, False)])
def test_phone_validator(value, ok):
    assert phone_ok(value) is ok


@pytest.mark.parametrize(
    "payload",
    [
        "1 " * 50_000,
        "a" * 100_000,
        "+" + "1" * 100_000,
        "1-" * 50_000,
        "(" * 100_000,
        "a@" * 50_000,
        "IL62 " * 20_000,
        "1." * 50_000,
    ],
    ids=["digits-spaces", "letters", "plus-digits", "digits-dashes", "brackets", "at-signs", "iban-like", "dotted"],
)
def test_adversarial_input_is_fast(payload):
    start = time.perf_counter()
    redact(payload, {})
    assert time.perf_counter() - start < 1.0


def test_random_garbage_does_not_crash():
    rnd = random.Random(7)
    alphabet = string.printable + "ёшщ שלום 🙂"
    for _ in range(100):
        text = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 300)))
        mapping = {}
        restore(redact(text, mapping), mapping)