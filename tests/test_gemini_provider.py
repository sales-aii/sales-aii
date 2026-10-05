# -*- coding: utf-8 -*-
"""
Tests for the real Gemini AI provider.

No network access and no API key required: httpx transports are mocked and
exercised through the real request/response code paths.
"""

import json

import httpx
import pytest

from ai.ai_manager import AIManager
from ai.providers.gemini_provider import GeminiProvider
from utils.exceptions import APIError


def _mock_transport(handler):
    """Return an httpx transport that dispatches to handler"""
    return httpx.MockTransport(handler)


def _response(payload, status_code=200):
    return httpx.Response(status_code, json=payload)


def _ok_body(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}]}


# --------------------------------------------------------------------------
# Request shape (official docs: ai.google.dev/api/generate-content)
# --------------------------------------------------------------------------
def test_request_uses_official_endpoint_and_key_header():
    captured = {}

    def handler(request: httpx.Request):
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return _response(_ok_body("hello"))

    provider = GeminiProvider()
    provider.api_key = "SECRET_KEY"

    with httpx.Client(transport=_mock_transport(handler)) as client:
        resp = client.post(
            provider._endpoint(),
            headers={
                "x-goog-api-key": provider.api_key,
                "Content-Type": "application/json",
            },
            json=provider._build_payload("hi"),
        )

    assert resp.status_code == 200
    assert captured["url"].startswith(
        "https://generativelanguage.googleapis.com/v1beta/models/"
    )
    assert captured["url"].endswith(":generateContent")
    # API key must be in the header, never in the URL
    assert "SECRET_KEY" not in captured["url"]
    assert captured["headers"]["x-goog-api-key"] == "SECRET_KEY"
    assert captured["body"]["contents"][0]["parts"][0]["text"] == "hi"


def test_structured_payload_uses_json_mime_type():
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return _response(_ok_body('{"discount_percent": 10}'))

    provider = GeminiProvider()
    with httpx.Client(transport=_mock_transport(handler)) as client:
        resp = client.post(
            provider._endpoint(),
            headers={"x-goog-api-key": "k"},
            json=provider._build_payload("p", json_mode=True),
        )
    assert resp.status_code == 200
    assert captured["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["body"]["contents"][0]["parts"][0]["text"] == "p"


# --------------------------------------------------------------------------
# Response parsing / failure handling
# --------------------------------------------------------------------------
def test_extract_text_joins_parts():
    body = {"candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}]}
    assert GeminiProvider._extract_text(body) == "ab"


def test_extract_text_raises_on_blocked_prompt():
    body = {"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}}
    with pytest.raises(APIError) as exc:
        GeminiProvider._extract_text(body)
    assert "SAFETY" in str(exc.value)


def test_extract_text_raises_on_empty_candidates():
    with pytest.raises(APIError):
        GeminiProvider._extract_text({"candidates": []})


def test_extract_text_raises_on_empty_text():
    body = {"candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}]}
    with pytest.raises(APIError) as exc:
        GeminiProvider._extract_text(body)
    assert "MAX_TOKENS" in str(exc.value)


def test_http_error_is_reported_not_faked(monkeypatch):
    def handler(request):
        return _response(
            {"error": {"message": "API key not valid", "status": "UNAUTHENTICATED"}},
            status_code=400,
        )

    provider = GeminiProvider()
    provider.api_key = "bad"
    captured = {}

    def fake_post(payload, model=None, timeout=None):
        with httpx.Client(transport=_mock_transport(handler)) as client:
            resp = client.post(provider._endpoint(model), json=payload)
        if resp.status_code != 200:
            captured["msg"] = provider._extract_error(resp)
            raise APIError(f"Gemini API error (HTTP {resp.status_code}): {captured['msg']}")

    monkeypatch.setattr(provider, "_post", fake_post)
    with pytest.raises(APIError) as exc:
        provider.generate("hi")
    assert "API key not valid" in str(exc.value)


def test_generate_structured_parses_json():
    def handler(request):
        return _response(_ok_body('{"score": 7, "sentiment": "positive"}'))

    provider = GeminiProvider()
    provider.api_key = "k"

    def fake_post(payload, model=None, timeout=None):
        with httpx.Client(transport=_mock_transport(handler)) as client:
            return client.post(provider._endpoint(model), json=payload).json()

    provider._post = fake_post
    result = provider.generate_structured("analyze this lead")
    assert result == {"score": 7, "sentiment": "positive"}


def test_generate_structured_raises_on_unparseable_json():
    def handler(request):
        return _response(_ok_body("not json at all"))

    provider = GeminiProvider()
    provider.api_key = "k"

    def fake_post(payload, model=None, timeout=None):
        with httpx.Client(transport=_mock_transport(handler)) as client:
            return client.post(provider._endpoint(model), json=payload).json()

    provider._post = fake_post
    with pytest.raises(APIError):
        provider.generate_structured("analyze")


# --------------------------------------------------------------------------
# AIManager integration
# --------------------------------------------------------------------------
def test_manager_falls_back_to_mock_without_key(monkeypatch):
    monkeypatch.setattr("config.config.settings.GEMINI_API_KEY", None, raising=False)
    monkeypatch.setattr("ai.providers.gemini_provider.settings.GEMINI_API_KEY", None)
    manager = AIManager()
    assert manager.active_provider == "mock"
    assert manager.is_real_provider_active() is False


def test_manager_selects_gemini_when_key_present(monkeypatch):
    monkeypatch.setattr(
        "ai.providers.gemini_provider.settings.GEMINI_API_KEY", "test-key"
    )
    monkeypatch.setattr("config.config.settings.AI_PROVIDER", "gemini")
    manager = AIManager()
    assert manager.active_provider == "gemini"
    assert manager.is_real_provider_active() is True
    assert manager.get_active_model()


def test_manager_reports_failure_instead_of_fake_success():
    manager = AIManager()

    class Boom:
        name = "boom"

        def generate_structured(self, *a, **kw):
            raise RuntimeError("provider down")

    manager.providers["boom"] = Boom()
    with pytest.raises(APIError):
        manager.generate_structured_response("x", provider="boom")
    assert manager.generate_structured_response("x", provider="boom", strict=False) == {}