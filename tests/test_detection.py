
from collections import defaultdict

import pytest

from api.services.logic.general import find_spans

VALUES = {
    "EMAIL": ["anna@corp.io", "first.last+tag@sub.example.co.uk", "user_1@mail.example.org", "a.b@x.dev"],
    "CARD": ["4111 1111 1111 1111", "5555-5555-5555-4444", "378282246310005", "6011 1111 1111 1117", "4012888888881881"],
    "IBAN": ["GB82 WEST 1234 5698 7654 32", "DE89 3704 0044 0532 0130 00", "IL62 0108 0000 0009 9999 999", "FR14 2004 1010 0505 0001 3M02 606", "IL62010800000009999999"],
    "IP": ["192.168.1.10", "8.8.8.8", "10.0.0.255", "203.0.113.7"],
    "PHONE": ["+972 54-123-4567", "+1 (415) 555-2671", "+44 20 7946 0958", "054-1234567", "+7 912 345-67-89"],
}

TEMPLATES = [
    "{v}",
    "Contact: {v}.",
    "please use {v} for this",
    "({v})",
    "line one\n{v}\nline three",
    "שלום {v} תודה",
]

NEGATIVES = [
    "Meeting on 2024-01-15 at 10:30",
    "Date 15.01.2024",
    "ID 4111 1111 1111 1112",  
    "uuid 123e4567-e89b-12d3-a456-426614174000",
    "2024-01-15T10:30:00Z",
    "call me at 12345",
    "price is $1,299.99",
    "see section 3.2.1 of the spec",
    "Hello, world! Nothing here.",
    "email me at name at example dot com",
    "שלום, מה שלומך?",
]


def build_corpus():
    corpus = []
    for label, values in VALUES.items():
        for value in values:
            for tpl in TEMPLATES:
                corpus.append((tpl.format(v=value), {(label, value)}))
    for text in NEGATIVES:
        corpus.append((text, set()))
    return corpus


def predict(text):
    return {(label, text[s:e]) for s, e, label in find_spans(text)}


def evaluate():
    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    for text, expected in build_corpus():
        got = predict(text)
        for item in got & expected:
            tp[item[0]] += 1
        for item in got - expected:
            fp[item[0]] += 1
        for item in expected - got:
            fn[item[0]] += 1
    report = {}
    for label in VALUES:
        p = tp[label] / (tp[label] + fp[label]) if tp[label] + fp[label] else 1.0
        r = tp[label] / (tp[label] + fn[label]) if tp[label] + fn[label] else 1.0
        report[label] = {"precision": p, "recall": r, "tp": tp[label], "fp": fp[label], "fn": fn[label]}
    return report


def test_print_report(capsys):
    report = evaluate()
    with capsys.disabled():
        print("\n\nlabel    precision  recall   tp   fp   fn")
        for label, m in report.items():
            print(f"{label:<8} {m['precision']:>9.2f} {m['recall']:>7.2f} {m['tp']:>4} {m['fp']:>4} {m['fn']:>4}")


@pytest.mark.parametrize("label", list(VALUES))
def test_recall_target(label):
    assert evaluate()[label]["recall"] >= 0.95


@pytest.mark.parametrize("label", list(VALUES))
def test_precision_target(label):
    assert evaluate()[label]["precision"] >= 0.90


def test_every_corpus_item_is_exactly_right():
    for text, expected in build_corpus():
        assert predict(text) == expected, text


KNOWN_FALSE_POSITIVES = [
("Order #123456789012", "any 9-15 digit number is considered a phone number"),
("ts=1700000000", "unix timestamp is considered a phone number"),
("SKU 12345-67890-1234", "article is considered a phone number"),
("pi=3.14159265358979", "long decimal fraction is considered a phone number"),
("version 1.2.3.4", "four-digit version is considered IPv4"),
("999.999.999.999", "octets greater than 255 are not checked"),
]
@pytest.mark.parametrize("text, reason", KNOWN_FALSE_POSITIVES, ids=[t for t, _ in KNOWN_FALSE_POSITIVES])
@pytest.mark.xfail(strict=True, reason="known limitation of regex detectors")
def test_known_false_positive(text, reason):
    assert predict(text) == set()


KNOWN_MISSES = [
    ("Anna Cohen lives on Herzl Street 5", "names and addresses are not detected (NER required)"),
    ("anna [at] corp [dot] io", "obfuscated email"),
]


@pytest.mark.parametrize("text, reason", KNOWN_MISSES, ids=[t for t, _ in KNOWN_MISSES])
@pytest.mark.xfail(strict=True, reason="known limitation: not detected yet")
def test_known_miss(text, reason):
    assert predict(text) != set()