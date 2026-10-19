# SharkEyes

Local PII/secret redaction and prompt-injection guard for LLM calls.
Hebrew-, Russian- and English-aware. **Zero dependencies, zero servers, zero telemetry** —
it runs inside your own FastAPI process, so personal data never leaves your infrastructure
on the way to an LLM provider.

```
user text ──► redact ──► [NAME_1] [EMAIL_1] [PHONE_1] ──► LLM provider
user sees ◄── restore ◄── "…send it to [EMAIL_1]…"    ◄── LLM provider
```

## Quick start

```python
from sharkeyes import Shield

shield = Shield(on_injection="raise")

# One line around your existing async LLM call:
chat = shield.wrap(call_llm)          # async def call_llm(messages) -> str
answer = await chat(messages)

# Or explicit control:
with shield.session() as s:
    safe = s.redact_messages(messages)       # provider only ever sees placeholders
    reply = await call_llm(safe)
    answer = s.restore(reply)
```

### FastAPI

```python
from sharkeyes.contrib_fastapi import install, session_dependency

install(app)                                    # InjectionBlocked -> HTTP 400
get_session = session_dependency(shield)

@app.post("/chat")
async def chat(body: In, session = Depends(get_session)):
    safe = session.redact_messages(msgs(body))
    return {"reply": session.restore(await call_llm(safe))}
```

Streaming works too (placeholders split across chunks are reassembled on the fly):
see `examples/demo_app.py`. Run `python examples/run_demo.py` for a walkthrough.

## What it detects

| Kind | Notes |
|---|---|
| `EMAIL`, `IP` | |
| `PHONE` | Israeli mobile/landline (`050-…`, `+972…`) and generic international |
| `IL_ID` | Israeli Teudat Zehut, **checksum-verified** |
| `CARD` | Luhn-verified |
| `IBAN` | mod-97-verified |
| `SECRET` | API keys (OpenAI/Anthropic-style, AWS, GitHub, Slack), JWTs, PEM private keys |
| `NAME` | heuristic: only after an introduction phrase ("my name is…", "שמי…", "меня зовут…") |

Prompt-injection scanner: English, Hebrew, Russian patterns, role spoofing, hidden
zero-width/bidi-override characters, exfiltration via URLs/markdown images. Reports contain
signal names only — never user text — so they are safe to log.

## Honest limitations

- **Names are the weak spot.** Regex can't find a name that isn't introduced. For that you need an NER model; plug one in as a custom `Detector`.
- **The injection scanner is heuristic.** It stops lazy attacks, not determined ones. Pair it with least-privilege tool access and output validation.
- **Models can mangle placeholders** (rare, but possible). Unknown placeholders are left as-is, never guessed.
- **Text only.** Images, PDFs and audio are not inspected.
- **This is a risk-reduction tool, not a compliance certificate.** It helps you prepare for GDPR / Israeli Privacy Protection Law obligations; it does not make you compliant by itself.

## Develop

```
pip install -e .[dev]
pytest
```
## License

AGPL-3.0
