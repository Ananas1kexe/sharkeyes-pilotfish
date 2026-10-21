
import time

import pytest

from sharkeyes import Shield, default_detectors, find_all
from sharkeyes.stream import StreamRestorer


def redact(text):
    with Shield().session() as s:
        return s.redact(text)

PROVIDER_TOKENS = {
    "anthropic": "sk-" + "ant-" + "api03-" + "A1b2" * 10,
    "openai": "sk-" + "proj-" + "Ab1" * 15,
    "openai_classic": "sk-" + "Ab1" * 16,
    "pypi": "pypi-" + "AgEIcHlwaS5vcmc" + "A1b_" * 30,
    "testpypi": "pypi-" + "AgENdGVzdC5weXBpLm9yZw" + "A1b_" * 30,
    "npm": "npm_" + "aB3" * 12,
    "github_classic": "gh" + "p_" + "aB3" * 12,
    "github_oauth": "gh" + "o_" + "aB3" * 12,
    "github_fine_grained": "github_" + "pat_" + "A1" * 11 + "_" + "b2" * 30,
    "gitlab": "gl" + "pat-" + "aB3-" * 6,
    "rubygems": "rubygems_" + "ab12" * 12,
    "docker_hub": "dckr_" + "pat_" + "aB3_" * 7,
    "aws_access_key": "AK" + "IA" + "ABCD1234" * 2,
    "aws_temp_key": "AS" + "IA" + "ABCD1234" * 2,
    "google_api": "AI" + "za" + "aB3_-" * 7,
    "google_oauth": "ya" + "29." + "aB3-" * 10,
    "stripe_secret": "sk_" + "live_" + "aB3" * 10,
    "stripe_restricted": "rk_" + "test_" + "aB3" * 10,
    "slack_bot": "xo" + "xb-" + "1234567890-" + "aB3" * 8,
    "huggingface": "hf_" + "aB3" * 12,
    "sendgrid": "SG." + ("aB3-_x" * 4)[:22] + "." + ("Zy9-_k" * 8)[:43],
    "shopify": "shp" + "at_" + "ab12" * 8,
    "digitalocean": "dop_" + "v1_" + "ab12" * 16,
    "supabase": "sbp_" + "ab12" * 10,
    "mailgun": "key-" + "ab12" * 8,
    "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbU",
}


@pytest.mark.parametrize("name", sorted(PROVIDER_TOKENS))
def test_service_token_is_fully_replaced(name):
    tok = PROVIDER_TOKENS[name]
    assert redact(f"export TOKEN={tok} # done") == "export TOKEN=[SECRET_1] # done"


@pytest.mark.parametrize("name", sorted(PROVIDER_TOKENS))
def test_service_token_survives_quotes_and_punctuation(name):
    tok = PROVIDER_TOKENS[name]
    assert redact(f'"{tok}"') == '"[SECRET_1]"'
    assert redact(f"({tok}),") == "([SECRET_1]),"


def test_same_token_gets_same_placeholder_different_tokens_differ():
    a, b = PROVIDER_TOKENS["github_classic"], PROVIDER_TOKENS["npm"]
    assert redact(f"{a} and {a} and {b}") == "[SECRET_1] and [SECRET_1] and [SECRET_2]"


@pytest.mark.parametrize(
    "text",
    [
        "task_force_asia is fine",
        "the sk-learn library",
        "use the sk- prefix",
        "AKIA is only a prefix",
        "ghp_ is a github prefix",
        "pypi-simple package",
        "run npm_install script",
        "a key-value store",
        "key-aaaaaaaaaa",
        "hf_ is hugging face",
        "eyJ is how base64 json starts",
        "visit https://hooks.slack.com/docs for help",
        "ASIA" + "B" * 5,
        "mykey-" + "ab12" * 8,      
        "xoxb is a slack prefix",
        "SG. is not enough",
    ],
)
def test_service_token_lookalikes_are_left_alone(text):
    assert redact(text) == text


def test_token_pattern_does_not_cut_a_longer_word():
    tok = PROVIDER_TOKENS["github_classic"]
    glued = tok + "_extra_word"
    assert redact(glued) == glued


def test_slack_webhook():
    url = "https://hooks.slack.com/services/T0123ABCD/B0123ABCD/" + "aB3" * 8
    assert redact(f"post to {url} now") == "post to [SECRET_1] now"


def test_telegram_bot_token():
    tok = "123456789:" + ("aB3-_x" * 6)[:35]
    assert redact(f"bot {tok}") == "bot [SECRET_1]"
    assert redact("time 12:30:45") == "time 12:30:45"


def test_discord_bot_token():
    tok = "M" + ("aB3" * 8)[:24] + "." + "aB3xYz" + "." + ("aB3" * 10)[:30]
    assert redact(f"token {tok}") == "token [SECRET_1]"


def test_twilio_sid():
    assert redact("sid AC" + "ab12" * 8) == "sid [SECRET_1]"
    assert redact("sid SK" + "ab12" * 8 + " ok") == "sid [SECRET_1] ok"


def test_azure_account_key_keeps_surrounding_text():
    text = "AccountName=x;AccountKey=" + "aB3" * 20 + "==;EndpointSuffix=core.windows.net"
    assert redact(text) == "AccountName=x;AccountKey=[SECRET_1];EndpointSuffix=core.windows.net"


def test_npmrc_auth_token():
    text = "//registry.npmjs.org/:_authToken=" + PROVIDER_TOKENS["npm"]
    assert redact(text) == "//registry.npmjs.org/:_authToken=[SECRET_1]"


def test_aws_secret_only_with_context():
    secret = ("aB3/+" * 8)[:40]
    assert redact("aws_secret_access_key = " + secret) == "aws_secret_access_key = [SECRET_1]"
    assert redact("AWS_SECRET_ACCESS_KEY=" + secret) == "AWS_SECRET_ACCESS_KEY=[SECRET_1]"
    assert redact("random " + secret) == "random " + secret


BEARER_TOKEN = "abcdefghijklmnop1234"


@pytest.mark.parametrize(
    "text,expected",
    [
        (f"Authorization: Bearer {BEARER_TOKEN}", "Authorization: Bearer [BEARER_1]"),
        (f"authorization: bearer {BEARER_TOKEN}", "authorization: bearer [BEARER_1]"),
        (f"AUTHORIZATION: BEARER {BEARER_TOKEN}", "AUTHORIZATION: BEARER [BEARER_1]"),
        (f"Bearer\t{BEARER_TOKEN}", "Bearer\t[BEARER_1]"),
        (f'{{"Authorization": "Bearer {BEARER_TOKEN}"}}', '{"Authorization": "Bearer [BEARER_1]"}'),
        (f"curl -H 'Authorization: Bearer {BEARER_TOKEN}' https://api.example.com", "curl -H 'Authorization: Bearer [BEARER_1]' https://api.example.com"),
        (f"Bearer abc._~+/=-{BEARER_TOKEN}", "Bearer [BEARER_1]"),
    ],
)
def test_bearer_token_replaced_keep_the_word(text, expected):
    assert redact(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "the bearer of bad news",
        "Bearer abc",                      
        "bearer of the 15th century ring",
        "Bearer",
        "bearer-bonds are boring",
    ],
)
def test_bearer_lookalikes_untouched(text):
    assert redact(text) == text


def test_same_bearer_token_twice_same_placeholder():
    t = f"Bearer {BEARER_TOKEN} then Bearer {BEARER_TOKEN} then Bearer {BEARER_TOKEN}x"
    assert redact(t) == "Bearer [BEARER_1] then Bearer [BEARER_1] then Bearer [BEARER_2]"


def test_bearer_with_jwt_never_leaks_the_jwt():
    out = redact("Authorization: Bearer " + PROVIDER_TOKENS["jwt"])
    assert PROVIDER_TOKENS["jwt"] not in out
    assert out.startswith("Authorization: Bearer [")



@pytest.mark.parametrize(
    "text,expected",
    [
        ("cvv: 123", "cvv: [CVV_1]"),
        ("CVV 4567", "CVV [CVV_1]"),
        ("CVC 4567", "CVC [CVV_1]"),
        ("cvv2: 456", "cvv2: [CVV_1]"),
        ("CV2=987", "CV2=[CVV_1]"),
        ("security code 321", "security code [CVV_1]"),
        ("Security Code: 3210", "Security Code: [CVV_1]"),
        ("cvv#123", "cvv#[CVV_1]"),
    ],
)
def test_cvv_variants(text, expected):
    assert redact(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "cvv is on the back",
        "cvv 12",
        "cvv 12345",
        "cvc 12",
        "cvvx 123",
        "my cvv number is on the back",
        "the security code was changed",
    ],
)
def test_cvv_lookalikes_untouched(text):
    assert redact(text) == text


def test_cvv_and_card_in_the_same_message():
    assert redact("card 4111 1111 1111 1111 cvv 123") == "card [CARD_1] cvv [CVV_1]"


def test_cvv_same_value_same_placeholder_new_value_new_placeholder():
    assert redact("cvv 123 and cvv 123 and cvv 456") == "cvv [CVV_1] and cvv [CVV_1] and cvv [CVV_2]"


BTC = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"


def test_bitcoin_bech32_address():
    assert redact(f"send to {BTC} please") == "send to [BITCOIN_1] please"
    assert redact(f"({BTC}),") == "([BITCOIN_1]),"
    assert redact(f"{BTC} and {BTC}") == "[BITCOIN_1] and [BITCOIN_1]"


@pytest.mark.parametrize(
    "text",
    [
        "bc1 is a prefix",
        "abc1qar0abc1qar0abc1qar0",
        "x" + BTC,            
        BTC + "1",            
        "bc1" + "q" * 5,
    ],
)
def test_bitcoin_lookalikes_untouched(text):
    assert redact(text) == text


def test_ethereum_address_any_case_and_exact_length():
    assert redact("to 0x" + "ab12" * 10) == "to [CRYPTO_1]"
    assert redact("to 0x" + "AB12" * 10) == "to [CRYPTO_1]"
    assert redact("0x" + "ab12" * 10 + ".") == "[CRYPTO_1]."
    assert redact("0x" + "ab1" * 13) == "0x" + "ab1" * 13           
    assert redact("0x" + "ab12" * 10 + "a") == "0x" + "ab12" * 10 + "a" 
    assert redact("call 0x1234 now") == "call 0x1234 now"



MIXED = (
    "Hi, my name is Dana Levi, mail dana@example.com, tel 050-123-4567. "
    f"Authorization: Bearer {BEARER_TOKEN}. Wallet {BTC}. "
    "Card 4111 1111 1111 1111 cvv 123. Server 192.168.1.10. "
    f"Key {PROVIDER_TOKENS['github_classic']}."
)
MIXED_VALUES = [
    "Dana Levi", "dana@example.com", "050-123-4567", BEARER_TOKEN, BTC,
    "4111 1111 1111 1111", "192.168.1.10", PROVIDER_TOKENS["github_classic"],
]


def test_mixed_message_leaves_no_raw_value_behind():
    out = redact(MIXED)
    for value in MIXED_VALUES:
        assert value not in out, value
    assert " cvv [CVV_1]" in out


def test_mixed_message_round_trip_is_exact():
    with Shield().session() as s:
        safe = s.redact(MIXED)
        assert s.restore(safe) == MIXED


def test_find_all_returns_sorted_non_overlapping_matches():
    ms = find_all(MIXED, default_detectors())
    assert ms == sorted(ms, key=lambda m: m.start)
    for a, b in zip(ms, ms[1:]):
        assert a.end <= b.start


def test_summary_counts_but_never_shows_values():
    with Shield().session() as s:
        s.redact(MIXED)
        summary = str(s.summary())
        for value in MIXED_VALUES:
            assert value not in summary
        assert s.summary()["redacted_distinct"]["BITCOIN"] == 1
        assert s.summary()["redacted_distinct"]["CVV"] == 1


def test_vault_wiped_after_new_kinds():
    shield = Shield()
    with shield.session() as s:
        s.redact(MIXED)
        assert len(s.vault) > 0
    assert len(s.vault) == 0


@pytest.mark.parametrize("size", [1, 2, 3, 5, 7, 50])
def test_stream_restore_for_new_placeholder_kinds(size):
    with Shield().session() as s:
        s.redact(MIXED)
        reply = "Use [BEARER_1] and [BITCOIN_1] with [CVV_1] and [SECRET_1] and [IP_1]. Odd [BEARER_9] and [x"
        chunks = [reply[i : i + size] for i in range(0, len(reply), size)]
        assert "".join(s.restore_iter(chunks)) == s.restore(reply)


def test_stream_holds_back_only_the_partial_placeholder():
    with Shield().session() as s:
        s.redact(f"Authorization: Bearer {BEARER_TOKEN}")
        r = StreamRestorer(s.vault)
        assert r.feed("Token [BEAR") == "Token "
        assert r.feed("ER_1] ok") == BEARER_TOKEN + " ok"


@pytest.mark.parametrize(
    "text",
    [
        "Can you explain what a bearer token is and why a cvv code is printed on cards?",
        "Привет! Подскажите, как сменить пароль и где найти токен доступа?",
        "שלום, אני צריך עזרה עם הטוקן והסיסמה שלי",
        "The key to success is a good key-value store and a short token lifetime.",
        "Version 1.2.3 released 2024-01-05; see https://example.com/docs/key-rotation",
    ],
)
def test_normal_conversation_is_not_touched(text):
    assert redact(text) == text


def test_multiple_new_kinds_inside_chat_messages():
    with Shield().session() as s:
        out = s.redact_messages(
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Use Bearer {BEARER_TOKEN} and pay {BTC}, cvv 123"},
            ]
        )
        assert out[0]["content"] == "You are a helpful assistant."
        assert out[1]["content"] == "Use Bearer [BEARER_1] and pay [BITCOIN_1], cvv [CVV_1]"



HOSTILE = {
    "letters": "a" * 200_000,
    "digits": "1" * 200_000,
    "sk-": "sk-" * 70_000,
    "bc1": "bc1" * 70_000,
    "0x": "0x" * 100_000,
    "bearer": "Bearer " * 30_000,
    "bearer-long": "Bearer " + "a" * 200_000,
    "cvv": "cvv " * 50_000,
    "cvv:": "cvv:" * 50_000,
    "key-": "key-" * 50_000,
    "ghp_": "gh" + "p_" * 50_000,
    "akia": "AKIA" * 50_000,
    "eyj": "eyJ" * 70_000,
    "eyj-dots": "eyJ" + "a." * 100_000,
    "xoxb": "xoxb-" * 40_000,
    "pypi": "pypi-AgEIcHlwaS5vcmc" * 10_000,
    "ip-dots": "1." * 100_000,
    "at-signs": "a@" * 100_000,
    "colons": "1:" * 100_000,
    "authtoken": "_authToken=" * 20_000,
    "accountkey": "AccountKey=" * 20_000,
    "aws-ctx": "aws_secret_access_key=" * 10_000,
    "webhook": "https://hooks.slack.com/services/T" * 10_000,
}


@pytest.mark.parametrize("name", sorted(HOSTILE))
def test_hostile_input_finishes_quickly(name):
    blob = HOSTILE[name]
    t0 = time.perf_counter()
    redact(blob)
    elapsed = time.perf_counter() - t0
    assert elapsed < 3.0, f"{name}: {elapsed:.2f}s"