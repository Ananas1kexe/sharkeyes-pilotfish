import time

import pytest

from main import app as app_module


def test_redact_returns_session_and_placeholders(client):
    r = client.post("/v1/redact", json={"text": "write to anna@corp.io"})
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "write to [EMAIL_1]"
    assert body["entities"] == 1
    assert len(body["session_id"]) >= 20


def test_redact_then_restore_roundtrip(client):
    r = client.post("/v1/redact", json={"text": "write to anna@corp.io"}).json()
    back = client.post("/v1/restore", json={"text": "ok [EMAIL_1]", "session_id": r["session_id"]})
    assert back.status_code == 200
    assert back.json()["text"] == "ok anna@corp.io"


def test_session_keeps_numbering_across_calls(client):
    sid = client.post("/v1/redact", json={"text": "a@b.io"}).json()["session_id"]
    second = client.post("/v1/redact", json={"text": "a@b.io and c@d.io", "session_id": sid}).json()
    assert second["session_id"] == sid
    assert second["text"] == "[EMAIL_1] and [EMAIL_2]"
    assert second["entities"] == 2


def test_sessions_are_isolated(client):
    a = client.post("/v1/redact", json={"text": "a@b.io"}).json()["session_id"]
    b = client.post("/v1/redact", json={"text": "other@x.io"}).json()["session_id"]
    assert a != b
    restored = client.post("/v1/restore", json={"text": "[EMAIL_1]", "session_id": b}).json()["text"]
    assert restored == "other@x.io"
    assert "a@b.io" not in restored


def test_session_ids_are_unique(client):
    ids = {client.post("/v1/redact", json={"text": "x"}).json()["session_id"] for _ in range(50)}
    assert len(ids) == 50


def test_unknown_session_on_restore_is_404(client):
    r = client.post("/v1/restore", json={"text": "x", "session_id": "nope"})
    assert r.status_code == 404


def test_unknown_session_on_redact_is_404_and_not_created(client):
    r = client.post("/v1/redact", json={"text": "a@b.io", "session_id": "chosen-by-caller"})
    assert r.status_code == 404
    assert "chosen-by-caller" not in app_module.SESSIONS


def test_expired_session_is_rejected_and_purged(client):
    sid = client.post("/v1/redact", json={"text": "a@b.io"}).json()["session_id"]
    app_module.SESSIONS[sid]["exp"] = time.time() - 1
    r = client.post("/v1/restore", json={"text": "[EMAIL_1]", "session_id": sid})
    assert r.status_code == 404
    assert sid not in app_module.SESSIONS


def test_session_ttl_is_extended_on_use(client):
    sid = client.post("/v1/redact", json={"text": "a@b.io"}).json()["session_id"]
    app_module.SESSIONS[sid]["exp"] = time.time() + 5
    client.post("/v1/redact", json={"text": "c@d.io", "session_id": sid})
    assert app_module.SESSIONS[sid]["exp"] > time.time() + app_module.SESSION_TTL - 5


def test_unknown_session_and_expired_look_the_same(client):
    sid = client.post("/v1/redact", json={"text": "a@b.io"}).json()["session_id"]
    app_module.SESSIONS[sid]["exp"] = time.time() - 1
    expired = client.post("/v1/restore", json={"text": "x", "session_id": sid})
    unknown = client.post("/v1/restore", json={"text": "x", "session_id": "zzz"})
    assert (expired.status_code, expired.json()) == (unknown.status_code, unknown.json())


def test_text_over_limit_is_rejected(client):
    r = client.post("/v1/redact", json={"text": "a" * 100_001})
    assert r.status_code == 422


def test_text_at_limit_is_accepted(client):
    r = client.post("/v1/redact", json={"text": "a" * 100_000})
    assert r.status_code == 200


@pytest.mark.parametrize("payload", [{}, {"text": 123}, {"text": None}])
def test_redact_rejects_bad_payload(client, payload):
    assert client.post("/v1/redact", json=payload).status_code == 422


def test_restore_requires_session_id(client):
    assert client.post("/v1/restore", json={"text": "x"}).status_code == 422


def test_no_pii_text_passes_through(client):
    body = client.post("/v1/redact", json={"text": "hello world"}).json()
    assert body["text"] == "hello world"
    assert body["entities"] == 0


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"content": [{"type": "text", "text": "ok"}]}

    def json(self):
        return self._payload


@pytest.fixture
def fake_llm(monkeypatch):
    calls = []
    state = {"response": FakeResponse()}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None):
            calls.append({"url": url, "headers": headers, "json": json})
            return state["response"]

    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeClient)
    return calls, state


CHAT_HEADERS = {"x-provider-key": "sk-test-123"}


def test_chat_sends_only_placeholders_and_restores_answer(client, fake_llm):
    calls, state = fake_llm
    state["response"] = FakeResponse(payload={"content": [{"type": "text", "text": "Wrote to [EMAIL_1]"}]})
    r = client.post(
        "/v1/chat",
        headers=CHAT_HEADERS,
        json={"messages": [{"role": "user", "content": "Draft a reply to anna@corp.io"}]},
    )
    assert r.status_code == 200
    assert r.json() == {"text": "Wrote to anna@corp.io", "entities_redacted": 1}

    sent = calls[0]["json"]
    assert "anna@corp.io" not in str(sent)
    assert sent["messages"][0]["content"] == "Draft a reply to [EMAIL_1]"
    assert "placeholders" in sent["system"]


def test_chat_uses_caller_key_and_correct_upstream(client, fake_llm):
    calls, _ = fake_llm
    client.post("/v1/chat", headers=CHAT_HEADERS, json={"messages": [{"role": "user", "content": "hi"}]})
    assert calls[0]["url"] == "https://api.anthropic.com/v1/messages"
    assert calls[0]["headers"]["x-api-key"] == "sk-test-123"


def test_chat_shares_mapping_between_messages(client, fake_llm):
    calls, _ = fake_llm
    client.post(
        "/v1/chat",
        headers=CHAT_HEADERS,
        json={
            "messages": [
                {"role": "user", "content": "I am anna@corp.io"},
                {"role": "assistant", "content": "Hello anna@corp.io"},
                {"role": "user", "content": "and also bob@corp.io"},
            ]
        },
    )
    contents = [m["content"] for m in calls[0]["json"]["messages"]]
    assert contents == ["I am [EMAIL_1]", "Hello [EMAIL_1]", "and also [EMAIL_2]"]


def test_chat_does_not_store_a_session(client, fake_llm):
    client.post("/v1/chat", headers=CHAT_HEADERS, json={"messages": [{"role": "user", "content": "a@b.io"}]})
    assert app_module.SESSIONS == {}


def test_chat_joins_multiple_text_blocks_and_skips_others(client, fake_llm):
    _, state = fake_llm
    state["response"] = FakeResponse(
        payload={"content": [{"type": "text", "text": "A "}, {"type": "tool_use", "id": "x"}, {"type": "text", "text": "B"}]}
    )
    r = client.post("/v1/chat", headers=CHAT_HEADERS, json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.json()["text"] == "A B"


def test_chat_upstream_error_returns_502_without_leaking_body(client, fake_llm):
    _, state = fake_llm
    state["response"] = FakeResponse(status_code=401, payload={"error": "secret upstream detail anna@corp.io"})
    r = client.post("/v1/chat", headers=CHAT_HEADERS, json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 502
    assert "secret upstream detail" not in r.text
    assert "401" in r.json()["detail"]


def test_chat_requires_provider_key(client, fake_llm):
    r = client.post("/v1/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"messages": [{"role": "system", "content": "x"}]}, 
        {"messages": [{"role": "user"}]},  
        {},  
        {"messages": [{"role": "user", "content": "x"}], "max_tokens": 9000},  
    ],
)
def test_chat_validates_payload(client, fake_llm, payload):
    r = client.post("/v1/chat", headers=CHAT_HEADERS, json=payload)
    assert r.status_code == 422


def test_chat_answer_with_unknown_placeholder_is_left_as_is(client, fake_llm):
    _, state = fake_llm
    state["response"] = FakeResponse(payload={"content": [{"type": "text", "text": "See [EMAIL_7]"}]})
    r = client.post("/v1/chat", headers=CHAT_HEADERS, json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.json()["text"] == "See [EMAIL_7]"