from collections import defaultdict

from core.config import DETECTORS, PLACEHOLDER_RE


def find_spans(text: str) -> list[tuple[int, int, str]]:
    candidates = []
    for priority, (label, rx, validator) in enumerate(DETECTORS):
        for m in rx.finditer(text):
            if validator is None or validator(m.group()):
                candidates.append((m.start(), priority, m.end(), label))
    candidates.sort()
    spans, last_end = [], 0
    for start, _, end, label in candidates:
        if start >= last_end:  
            spans.append((start, end, label))
            last_end = end
    return spans
 
 
def redact(text: str, mapping: dict[str, str]) -> str:
    reverse = {v: k for k, v in mapping.items()}
    counters: dict[str, int] = defaultdict(int)
    for placeholder in mapping:
        counters[placeholder.strip("[]").rsplit("_", 1)[0]] += 1
 
    out, pos = [], 0
    for start, end, label in find_spans(text):
        value = text[start:end]
        placeholder = reverse.get(value)
        if placeholder is None:
            counters[label] += 1
            placeholder = f"[{label}_{counters[label]}]"
            mapping[placeholder] = value
            reverse[value] = placeholder
        out += [text[pos:start], placeholder]
        pos = end
    out.append(text[pos:])
    return "".join(out)


def restore(text: str, mapping: dict[str, str]) -> str:
    return PLACEHOLDER_RE.sub(lambda m: mapping.get(m.group(), m.group()), text)
 

