# -*- coding: utf-8 -*-
"""
Telegram and Shopier integration tests.

Real HTTP calls are exercised through mocked httpx transports so no network
access and no API keys are required.
"""

import json
import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.exceptions import APIError  # noqa: E402


def _transport(handler):
    return httpx.MockTransport(handler)


def _patch_client(monkeypatch, handler):
    """Route utils.http_client.request through a mocked transport"""
    real_client_cls = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = _transport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


# ==========================================================================
# Telegram
# ==========================================================================
def test_telegram_requires_configuration(monkeypatch):
    from integrations.telegram import TelegramIntegration

    monkeypatch.setattr(
        "integrations.telegram.settings.TELEGRAM_BOT_TOKEN", None
    )
    monkeypatch.setattr(
        "integrations.telegram.settings.TELEGRAM_CHAT_ID", None
    )
    t = TelegramIntegration()
    assert t.is_configured() is False
    with pytest.raises(APIError) as exc:
        t.send_message("hello")
    assert "TELEGRAM_BOT_TOKEN" in str(exc.value)


def test_telegram_send_message_uses_official_endpoint(monkeypatch):
    from integrations.telegram import TelegramIntegration

    captured = {}

    def handler(request: httpx.Request):
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("integrations.telegram.settings.TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setattr("integrations.telegram.settings.TELEGRAM_CHAT_ID", "999")

    t = TelegramIntegration()
    assert t.send_message("hi") is True
    assert captured["url"] == "https://api.telegram.org/bot123:ABC/sendMessage"
    assert captured["body"] == {"chat_id": "999", "text": "hi"}


def test_telegram_send_message_returns_false_on_api_error(monkeypatch):
    """Telegram answering ok:false must NOT be reported as success"""
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        return httpx.Response(
            200, json={"ok": False, "error_code": 403, "description": "Forbidden"}
        )

    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("integrations.telegram.settings.TELEGRAM_BOT_TOKEN", "123:ABC")
    monkeypatch.setattr("integrations.telegram.settings.TELEGRAM_CHAT_ID", "999")

    t = TelegramIntegration()
    with pytest.raises(APIError) as exc:
        t.send_message("hi")
    assert "Forbidden" in str(exc.value)


def test_telegram_send_message_raises_on_http_error(monkeypatch):
    from integrations.telegram import TelegramIntegration

    def handler(request: httpx.Request):
        return httpx.Response(
            401, json={"ok": False, "description": "Unauthorized"}
        )

    _patch_client(monkeypatch, handler)
    monkeypatch.setattr(
        "integrations.telegram.settings.TELEGRAM_BOT_TOKEN",
        "123456789:revokedsecretvalue",
    )
    monkeypatch.setattr("integrations.telegram.settings.TELEGRAM_CHAT_ID", "1")

    t = TelegramIntegration()
    with pytest.raises(APIError) as exc:
        t.send_message("hi")
    assert "401" in str(exc.value)


def test_telegram_refuses_empty_message(monkeypatch):
    from integrations.telegram import TelegramIntegration

    monkeypatch.setattr(
        "integrations.telegram.settings.TELEGRAM_BOT_TOKEN",
        "123456789:anysecretvalue",
    )
    monkeypatch.setattr("integrations.telegram.settings.TELEGRAM_CHAT_ID", "1")
    with pytest.raises(APIError):
        TelegramIntegration().send_message("   ")


def test_telegram_try_notify_swallows_errors(monkeypatch):
    """try_notify must not break the caller flow"""
    from integrations.telegram import TelegramIntegration

    monkeypatch.setattr("integrations.telegram.settings.TELEGRAM_BOT_TOKEN", None)
    assert TelegramIntegration().try_notify("x") is False


def test_telegram_mock():
    """Test telegram mock (used by unit tests, never in production)"""
    from integrations.mock.telegram_mock import MockTelegramIntegration
    t = MockTelegramIntegration()
    assert t.test_notification() is True
    assert t.send_message("hi") is True


# ==========================================================================
# Shopier
# ==========================================================================
def test_shopier_requires_token(monkeypatch):
    from integrations.shopier import ShopierIntegration

    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_TOKEN", None)
    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_KEY", None)
    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_SECRET", None)

    s = ShopierIntegration()
    assert s.is_configured() is False
    with pytest.raises(APIError):
        s.check_payment_status("ref123")


def test_shopier_status_paid(monkeypatch):
    from integrations.shopier import ShopierIntegration

    def handler(request: httpx.Request):
        assert str(request.url).startswith("https://api.shopier.com/v1/orders/ref123")
        assert request.headers["Authorization"] == "Bearer PAT"
        return httpx.Response(
            200, json={"data": {"id": "ref123", "paymentStatus": "paid"}}
        )

    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_TOKEN", "PAT")

    res = ShopierIntegration().check_payment_status("ref123")
    assert res["status"] == "paid"
    assert res["paid"] is True


def test_shopier_status_unpaid_maps_to_pending(monkeypatch):
    from integrations.shopier import ShopierIntegration

    def handler(request: httpx.Request):
        return httpx.Response(
            200, json={"data": {"id": "ref1", "paymentStatus": "unpaid"}}
        )

    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_TOKEN", "PAT")

    res = ShopierIntegration().check_payment_status("ref1")
    assert res["status"] == "pending"
    assert res["paid"] is False


def test_shopier_refunded_order_maps_to_cancelled():
    from integrations.shopier import ShopierIntegration

    order = {
        "paymentStatus": "paid",
        "refunds": [{"status": "succeeded"}],
    }
    assert ShopierIntegration.map_payment_status(order) == "cancelled"


def test_shopier_failed_refund_maps_to_failed():
    from integrations.shopier import ShopierIntegration

    order = {"paymentStatus": "paid", "refunds": [{"status": "failed"}]}
    assert ShopierIntegration.map_payment_status(order) == "failed"


def test_shopier_unknown_status_never_maps_to_paid():
    from integrations.shopier import ShopierIntegration

    assert ShopierIntegration.map_payment_status({}) == "pending"
    assert ShopierIntegration.map_payment_status(None) == "pending"
    assert ShopierIntegration.map_payment_status({"paymentStatus": "???"}) == "pending"


def test_shopier_404_raises_instead_of_reporting_pending(monkeypatch):
    """A failed lookup must never look like a successful 'pending' result"""
    from integrations.shopier import ShopierIntegration

    def handler(request: httpx.Request):
        return httpx.Response(404, json={"error": "Order not found"})

    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_TOKEN", "PAT")

    with pytest.raises(APIError) as exc:
        ShopierIntegration().check_payment_status("missing")
    assert "404" in str(exc.value)


def test_shopier_verify_requires_order_recheck(monkeypatch):
    from integrations.shopier import ShopierIntegration

    calls = []

    def handler(request: httpx.Request):
        calls.append(str(request.url))
        return httpx.Response(
            200, json={"data": {"id": "ref9", "paymentStatus": "unpaid"}}
        )

    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_TOKEN", "PAT")

    res = ShopierIntegration().verify_payment({"orderId": "ref9"})
    assert res["verified"] is False
    assert res["status"] == "pending"
    # it must have re-read the order instead of trusting the payload
    assert len(calls) == 1


def test_shopier_verify_accepts_confirmed_payment(monkeypatch):
    from integrations.shopier import ShopierIntegration

    def handler(request: httpx.Request):
        return httpx.Response(
            200, json={"data": {"id": "ref9", "paymentStatus": "paid"}}
        )

    _patch_client(monkeypatch, handler)
    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_TOKEN", "PAT")

    res = ShopierIntegration().verify_payment({"orderId": "ref9"})
    assert res["verified"] is True
    assert res["status"] == "paid"


def test_shopier_verify_rejects_payload_without_order_id(monkeypatch):
    from integrations.shopier import ShopierIntegration

    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_TOKEN", "PAT")
    with pytest.raises(APIError):
        ShopierIntegration().verify_payment({"status": "paid"})
    with pytest.raises(APIError):
        ShopierIntegration().verify_payment({})


def test_shopier_mock():
    """Test shopier mock (used by unit tests, never in production)"""
    from integrations.mock.shopier_mock import MockShopierIntegration
    s = MockShopierIntegration()
    res = s.check_payment_status("x")
    assert res['status'] == 'pending'
    res2 = s.verify_payment({})
    assert res2['verified'] is False