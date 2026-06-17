from __future__ import annotations

from mana_analyzer.utils.redaction import REDACTED, redact_json_line, redact_secrets


def test_redact_secrets_recurses_into_nested_dicts_and_lists() -> None:
    payload = {
        "type": "init",
        "api_key": "sk-proj-secret",
        "model": "gpt",
        "headers": {
            "Authorization": "Bearer abc",
            "cookie": "session=xyz",
            "x-custom": "keep-me",
        },
        "items": [
            {"token": "t1", "ok": 1},
            {"refresh_token": "r1", "password": "p", "value": "keep"},
        ],
    }
    redacted = redact_secrets(payload)

    assert redacted["api_key"] == REDACTED
    assert redacted["headers"]["Authorization"] == REDACTED
    assert redacted["headers"]["cookie"] == REDACTED
    assert redacted["items"][0]["token"] == REDACTED
    assert redacted["items"][1]["refresh_token"] == REDACTED
    assert redacted["items"][1]["password"] == REDACTED

    # Non-sensitive values are preserved.
    assert redacted["model"] == "gpt"
    assert redacted["headers"]["x-custom"] == "keep-me"
    assert redacted["items"][0]["ok"] == 1
    assert redacted["items"][1]["value"] == "keep"

    # Original input is not mutated.
    assert payload["api_key"] == "sk-proj-secret"


def test_redact_secrets_is_case_insensitive_on_keys() -> None:
    assert redact_secrets({"API_KEY": "x"})["API_KEY"] == REDACTED
    assert redact_secrets({"Set-Cookie": "x"})["Set-Cookie"] == REDACTED


def test_redact_json_line_handles_full_json() -> None:
    raw = '{"type":"init","api_key":"sk-proj-secret","model":"gpt"}'
    out = redact_json_line(raw)
    assert "sk-proj-secret" not in out
    assert REDACTED in out
    assert "gpt" in out


def test_redact_json_line_handles_partial_text() -> None:
    raw = 'Received: "api_key": "sk-proj-abc" and Bearer sk-zzz999'
    out = redact_json_line(raw)
    assert "sk-proj-abc" not in out
    assert "sk-zzz999" not in out
    assert REDACTED in out
