import logging

import pytest

from main import app as app_module

SECRET_EMAIL = "canary.user.7731@secret-corp.example"
SECRET_CARD = "4111 1111 1111 1111"
SECRET_KEY = "sk-canary-key-99887766"
SECRETS = [SECRET_EMAIL, "4111 1111 1111 1111", "4111", SECRET_KEY]


@pytest.fixture
def fake_llm(monkeypatch):
    class Resp:
        status_code = 200

        def json(self):
            return {"content": [{"type": "text", "text": "reply for [EMAIL_1]"}]}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *a, **k):
            return Resp()

    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeClient)


def exercise_all_endpoints(client):
    text = f"Mail {SECRET_EMAIL} card {SECRET_CARD}"
    sid = client.post("/v1/redact", json={"text": text}).json()["session_id"]
    client.post("/v1/restore", json={"text": "[EMAIL_1]", "session_id": sid})
    client.post("/v1/restore", json={"text": text, "session_id": "unknown"})  
    client.post("/v1/redact", json={"text": text, "session_id": "unknown"})  
    client.post("/v1/redact", json={"text": 123})  
    client.post(
        "/v1/chat",
        headers={"x-provider-key": SECRET_KEY},
        json={"messages": [{"role": "user", "content": text}]},
    )


def test_secrets_never_appear_in_logs_or_output(client, fake_llm, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    exercise_all_endpoints(client)

    captured = capsys.readouterr()
    haystack = caplog.text + captured.out + captured.err
    for secret in SECRETS:
        assert secret not in haystack, f"{secret!r} leaked into logs or output"


def test_error_responses_do_not_echo_secrets(client):
    text = f"Mail {SECRET_EMAIL}"
    responses = [
        client.post("/v1/restore", json={"text": text, "session_id": "unknown"}),
        client.post("/v1/redact", json={"text": text, "session_id": "unknown"}),
    ]
    for r in responses:
        assert SECRET_EMAIL not in r.text


def test_redacted_output_contains_no_original_values(client):
    r = client.post("/v1/redact", json={"text": f"{SECRET_EMAIL} {SECRET_CARD}"}).json()
    assert SECRET_EMAIL not in r["text"]
    assert "4111" not in r["text"]


def test_provider_key_is_never_stored(client, fake_llm):
    client.post(
        "/v1/chat",
        headers={"x-provider-key": SECRET_KEY},
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert SECRET_KEY not in repr(app_module.SESSIONS)


def test_mapping_is_not_exposed_in_redact_response(client):
    body = client.post("/v1/redact", json={"text": SECRET_EMAIL}).json()
    assert set(body) == {"session_id", "text", "entities"}