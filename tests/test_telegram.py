# -*- coding: utf-8 -*-
"""
Telegram integration and connection-test tests.

All HTTP traffic is mocked, so the suite needs no real bot token and no chat id.
Endpoints are asserted against the official Bot API documentation:
- https://core.telegram.org/bots/api#getme
- https://core.telegram.org/bots/api#sendmessage

Telegram answers failures with a 4xx status and its own `description` field, so
the tests assert that the real API text survives all the way to the caller.
"""

import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.exceptions import APIError  # noqa: E402


def _patch_client(monkeypatch, handler):
    real_client_cls = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


def _configure_telegram(
    monkeypatch,
    token="123456789:AAHOOqS380CkMJVwQfM9khsio6DWoOqfOMw",
    chat_id="12345",
):
    monkeypatch.setattr(
        "integrations.telegram.settings.TELEGRAM_BOT_TOKEN", token
    )
    monkeypatch.setattr(
        "integrations.telegram.settings.TELEGRAM_CHAT_ID", chat_id
    )


# ==========================================================================
# Configuration
# ==========================================================================
def test_telegram_not_configured_without_env_values(monkeypatch):
    from integrations.telegram import TelegramIntegration

    _configure_telegram(monkeypatch, None, None)
    t = TelegramIntegration()
    assert t.is_configured() is False
    with pytest.raises(APIError) as exc:
        t.test_connection()
    assert "TELEGRAM_BOT_TOKEN" in str(exc.value)


def test_telegram_chat_id_missing_is_reported(monkeypatch):
    from integrations.telegram import TelegramIntegration

    _configure_telegram(monkeypatch, REAL_TOKEN, None)
    with pytest.raises(APIError) as exc:
        TelegramIntegration().test_connection()
    assert "TELEGRAM_CHAT_ID" in str(exc.value)


REAL_TOKEN = "123456789:AAHOOqS380CkMJVwQfM9khsio6DWoOqfOMw"


def test_constructor_overrides_take_precedence(monkeypatch):
    """The Settings form may hold a corrected value not yet written to .env"""
    from integrations.telegram import TelegramIntegration

    typed_token = "987654321:typedsecretvalue"
    _configure_telegram(monkeypatch, REAL_TOKEN, "ENV_CHAT")
    t = TelegramIntegration(bot_token=typed_token, chat_id="TYPED_CHAT")
    assert t.bot_token == typed_token
    assert t.chat_id == "TYPED_CHAT"
    assert t.is_configured() is True


def test_empty_override_falls_back_to_env(monkeypatch):
    from integrations.telegram import TelegramIntegration

    _configure_telegram(monkeypatch, REAL_TOKEN, "ENV_CHAT")
    t = TelegramIntegration(bot_token="", chat_id="")
    assert t.bot_token == REAL_TOKEN
    assert t.chat_id == "ENV_CHAT"


# ==========================================================================
# Token shape
# ==========================================================================
def test_token_without_the_bot_id_prefix_is_rejected_locally(monkeypatch):
    """
    A secret copied without its '<bot_id>:' prefix makes Telegram answer a bare
    404. Catching it locally turns that into an explanation.
    """
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        pytest.fail("no request may be made with a malformed token")

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch, "AAHOOqS380CkMJVwQfM9khsio6DWoOqfOMw")

    with pytest.raises(APIError) as exc:
        TelegramIntegration().test_connection()
    message = str(exc.value)
    assert "<bot_id>" in message
    assert "TELEGRAM_BOT_TOKEN" in message


@pytest.mark.parametrize(
    "value",
    [
        "123456789:AAHOOqS380CkMJVwQfM9khsio6DWoOqfOMw",  # documented shape
        "1:a",
    ],
)
def test_well_shaped_tokens_pass_the_format_check(value):
    from integrations.telegram import looks_like_bot_token

    assert looks_like_bot_token(value) is True


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "AAHOOqS380CkMJVwQfM9khsio6DWoOqfOMw",  # secret only, no prefix
        "not-a-number:secret",                    # prefix is not a bot id
        "123456789:",                            # no secret
        ":secret",                               # no bot id
    ],
)
def test_malformed_tokens_are_rejected(value):
    from integrations.telegram import looks_like_bot_token

    assert looks_like_bot_token(value) is False


# ==========================================================================
# Connection test
# ==========================================================================
def test_test_connection_calls_get_me_then_send_message(monkeypatch):
    """Both documented calls must happen, against the documented URLs"""
    from integrations.telegram import TelegramIntegration

    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        if request.url.path.endswith("/getMe"):
            return httpx.Response(
                200,
                json={"ok": True, "result": {"id": 7, "username": "sales_aii_bot"}},
            )
        return httpx.Response(
            200, json={"ok": True, "result": {"message_id": 42}}
        )

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch)

    result = TelegramIntegration().test_connection()

    assert len(calls) == 2
    assert calls[0].url.path == f"/bot{REAL_TOKEN}/getMe"
    assert calls[1].url.path == f"/bot{REAL_TOKEN}/sendMessage"
    assert result["bot_username"] == "sales_aii_bot"
    assert result["bot_id"] == 7
    assert result["chat_id"] == "12345"
    assert result["message_id"] == 42


def test_test_connection_sends_actual_message_body(monkeypatch):
    """The delivered text and chat id must be the ones we claim to send"""
    from integrations.telegram import TelegramIntegration

    bodies = []

    def handler(request: httpx.Request):
        if request.url.path.endswith("/sendMessage"):
            import json

            bodies.append(json.loads(request.content.decode()))
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})
        return httpx.Response(
            200, json={"ok": True, "result": {"id": 1, "username": "bot"}}
        )

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch, REAL_TOKEN, "998877")

    result = TelegramIntegration().test_connection()

    assert bodies[0]["chat_id"] == "998877"
    assert "Sales.aii" in bodies[0]["text"]
    assert bodies[0]["text"] == result["text"]
    assert bodies[0]["text"].strip() == bodies[0]["text"]


def test_invalid_token_reports_telegram_description(monkeypatch):
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        return httpx.Response(
            401,
            json={"ok": False, "error_code": 401, "description": "Unauthorized"},
        )

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch, "123456789:WRONGsecretvalue")

    with pytest.raises(APIError) as exc:
        TelegramIntegration().test_connection()
    message = str(exc.value)
    assert "401" in message
    assert "Unauthorized" in message
    assert "TELEGRAM_BOT_TOKEN" in message


def test_wrong_chat_id_reports_telegram_description(monkeypatch):
    """Token is fine, the chat is not: the send must fail loudly"""
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        if request.url.path.endswith("/getMe"):
            return httpx.Response(
                200, json={"ok": True, "result": {"id": 1, "username": "bot"}}
            )
        return httpx.Response(
            400,
            json={"ok": False, "error_code": 400, "description": "chat not found"},
        )

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch, REAL_TOKEN, "-1009999")

    with pytest.raises(APIError) as exc:
        TelegramIntegration().test_connection()
    message = str(exc.value)
    assert "chat not found" in message
    assert "400" in message


def test_bot_cannot_write_to_chat_reports_forbidden(monkeypatch):
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        if request.url.path.endswith("/getMe"):
            return httpx.Response(
                200, json={"ok": True, "result": {"id": 1, "username": "bot"}}
            )
        return httpx.Response(
            403,
            json={
                "ok": False,
                "error_code": 403,
                "description": "Forbidden: bot was blocked by the user",
            },
        )

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch)

    with pytest.raises(APIError) as exc:
        TelegramIntegration().test_connection()
    message = str(exc.value)
    assert "bot was blocked by the user" in message
    assert "/start" in message  # actionable hint


def test_ok_false_with_http_200_is_still_a_failure(monkeypatch):
    """Never report success unless Telegram confirms ok:true"""
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        if request.url.path.endswith("/getMe"):
            return httpx.Response(
                200, json={"ok": True, "result": {"id": 1, "username": "bot"}}
            )
        return httpx.Response(
            200,
            json={"ok": False, "error_code": 400, "description": "Bad Request"},
        )

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch)

    with pytest.raises(APIError) as exc:
        TelegramIntegration().test_connection()
    assert "Bad Request" in str(exc.value)


def test_missing_message_id_is_not_treated_as_success(monkeypatch):
    """ok:true with no message_id cannot prove delivery"""
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        if request.url.path.endswith("/getMe"):
            return httpx.Response(
                200, json={"ok": True, "result": {"id": 1, "username": "bot"}}
            )
        return httpx.Response(200, json={"ok": True, "result": {}})

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch)

    with pytest.raises(APIError) as exc:
        TelegramIntegration().test_connection()
    assert "message_id" in str(exc.value)


def test_network_failure_is_reported_not_swallowed(monkeypatch):
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        raise httpx.ConnectError("no route to host")

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch)

    with pytest.raises(APIError) as exc:
        TelegramIntegration().test_connection()
    assert "connection error" in str(exc.value)


def test_timeout_is_reported(monkeypatch):
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        raise httpx.ReadTimeout("too slow")

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch)

    with pytest.raises(APIError) as exc:
        TelegramIntegration().test_connection()
    assert "timed out" in str(exc.value)


# ==========================================================================
# Existing behaviour must stay intact
# ==========================================================================
def test_send_message_returns_true_on_confirmed_delivery(monkeypatch):
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 5}})

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch)
    assert TelegramIntegration().send_message("hello") is True


def test_send_message_refuses_empty_text(monkeypatch):
    from integrations.telegram import TelegramIntegration

    _patch_client(monkeypatch, lambda request: httpx.Response(200, json={}))
    _configure_telegram(monkeypatch)
    with pytest.raises(APIError) as exc:
        TelegramIntegration().send_message("   ")
    assert "empty" in str(exc.value)


def test_try_notify_returns_false_instead_of_raising(monkeypatch):
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        return httpx.Response(
            400,
            json={"ok": False, "error_code": 400, "description": "chat not found"},
        )

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch)
    assert TelegramIntegration().try_notify("hello") is False


def test_owner_notifications_still_reach_send_message(monkeypatch):
    """The pre-existing notification helpers must not be broken"""
    from integrations.telegram import TelegramIntegration

    sent = []

    def handler(request: httpx.Request):
        import json

        sent.append(json.loads(request.content.decode())["text"])
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 3}})

    _patch_client(monkeypatch, handler)
    _configure_telegram(monkeypatch)
    t = TelegramIntegration()

    t.notify_sale_completed({"total": 10})
    t.notify_final_offer({"lead": 1})
    t.notify_owner_intervention({"lead": 2})
    t.notify_critical_error("boom")
    t.notify_system_error("boom")

    assert len(sent) == 5
    assert "10" in sent[0]
    assert "lead" in sent[2]