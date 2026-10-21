from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .core.config import _BASE64_BLOB, _FLAGS, _HIDDEN, _NIQQUD

_PATTERNS: list[tuple[str, re.Pattern, float]] = [
    (
        "override_instructions_en",
        re.compile(
            r"\b(ignore|disregard|forget|override)\b[^.\n]{0,40}\b(previous|prior|above|earlier|all|any|your)\b"
            r"[^.\n]{0,30}\b(instructions?|prompts?|rules?|guidelines?|directives?)\b",
            _FLAGS,
        ),
        0.8,
    ),
    (
        "reveal_system_prompt_en",
        re.compile(
            r"\b(reveal|show|print|repeat|output|leak|display)\b[^.\n]{0,30}"
            r"\b(system|hidden|initial|secret)\s+(prompt|instructions?|message)\b",
            _FLAGS,
        ),
        0.7,
    ),
    (
        "persona_switch_en",
        re.compile(
            r"\byou\s+are\s+now\b|\bact\s+as\s+(an?\s+)?(dan|unfiltered|unrestricted|jailbroken)"
            r"|\bdeveloper\s+mode\b|\bjailbreak",
            _FLAGS,
        ),
        0.6,
    ),
    (
        "role_spoofing",
        re.compile(r"</?\s*(system|assistant)\s*>|^\s*#{1,3}\s*(system|assistant)\b|\[/?(inst|system)\]", _FLAGS),
        0.5,
    ),
    ("new_instructions_en", re.compile(r"\b(new|updated)\s+instructions?\s*:", _FLAGS), 0.4),
    (
        "exfil_to_url",
        re.compile(r"\b(send|post|forward|exfiltrate|upload)\b[^.\n]{0,50}\b(to|at)\b\s+https?://", _FLAGS),
        0.5,
    ),
    (
        "markdown_image_exfil",
        re.compile(r"!\[[^\]]*\]\(https?://[^)\s]*\?[^)]*\)", _FLAGS),
        0.4,
    ),
    # Hebrew
    ("override_instructions_he", re.compile(r"התעלמ(?:ו)?\s+מ(?:כל\s+)?ה?הוראות"), 0.8),
    ("forget_instructions_he", re.compile(r"שכח(?:ו)?\s+(?:את\s+)?(?:כל\s+)?ה?הוראות"), 0.8),
    (
        "reveal_system_prompt_he",
        re.compile(r"(?:הצג|הדפס|חשוף|גלה)[^.\n]{0,30}(?:פרומפט|הנחיות|הוראות)[^.\n]{0,15}מערכת"),
        0.7,
    ),
    ("persona_switch_he", re.compile(r"אתה\s+עכשיו\s+"), 0.3),
    # Russian
    (
        "override_instructions_ru",
        re.compile(r"(?:игнорируй|игнорируйте|забудь|забудьте|отмени)[^.\n]{0,40}(?:инструкци|указани|правил|промпт)", _FLAGS),
        0.8,
    ),
    (
        "reveal_system_prompt_ru",
        re.compile(r"(?:покажи|выведи|раскрой|напечатай)[^.\n]{0,30}системн\S*\s+(?:промпт|инструкци)", _FLAGS),
        0.7,
    ),
    ("pretend_en", re.compile(r"\bpretend\s+(that\s+)?you\s+(are|have)\b", _FLAGS), 0.4),
    ("persona_switch_ru", re.compile(r"\bты\s+теперь\s+", _FLAGS), 0.3),
]



@dataclass(frozen=True)
class Finding:
    name: str
    weight: float


@dataclass
class InjectionReport:
    score: float = 0.0
    findings: list[Finding] = field(default_factory=list)

    @property
    def level(self) -> str:
        if self.score >= 0.7:
            return "high"
        if self.score >= 0.4:
            return "medium"
        return "low" if self.score > 0 else "none"

    def __bool__(self) -> bool:
        return self.score > 0


def _normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    t = _HIDDEN.sub("", t)
    t = _NIQQUD.sub("", t)
    return t


def scan_injection(text: str) -> InjectionReport:
    findings: list[Finding] = []
    if _HIDDEN.search(text):
        findings.append(Finding("hidden_unicode", 0.4))
    norm = _normalize(text)
    for name, rx, weight in _PATTERNS:
        if rx.search(norm):
            findings.append(Finding(name, weight))
    if _BASE64_BLOB.search(text):
        findings.append(Finding("long_encoded_blob", 0.3))

    keep = 1.0
    for f in findings:
        keep *= 1.0 - f.weight
    return InjectionReport(score=round(1.0 - keep, 4), findings=findings)
