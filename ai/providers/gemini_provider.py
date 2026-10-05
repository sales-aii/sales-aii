# -*- coding: utf-8 -*-
"""
Gemini AI Provider - Google Gemini API
Official endpoint: POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
Docs: https://ai.google.dev/api/generate-content
"""

from typing import Dict, Any
import httpx
from ai.providers.base_provider import BaseAIProvider
from utils.exceptions import APIError
from config.config import settings


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini provider using REST API.
    API key is sent via x-goog-api-key header (never in URL / logs).
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    API_VERSION = "v1beta"

    def __init__(self, **kwargs):
        super().__init__('gemini', **kwargs)
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.temperature = kwargs.get('temperature', 0.7)
        self.max_output_tokens = kwargs.get('max_output_tokens', 2048)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _endpoint(self, model: str = None, json_mode: bool = False) -> str:
        model = model or self.model
        suffix = ":generateContent"
        return f"{self.BASE_URL}/{model}{suffix}"

    def _build_payload(self, prompt: str, json_mode: bool = False,
                       temperature: float = None, system: str = None) -> Dict[str, Any]:
        generation_config: Dict[str, Any] = {
            "temperature": temperature if temperature is not None else self.temperature,
            "maxOutputTokens": self.max_output_tokens,
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload: Dict[str, Any] = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ],
            "generationConfig": generation_config,
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        return payload

    def _post(self, payload: Dict[str, Any], model: str = None,
              timeout: int = None) -> Dict[str, Any]:
        """POST to Gemini and return parsed JSON response"""
        url = self._endpoint(model)
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=timeout or self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as e:
            raise APIError(f"Gemini request timed out: {e}")
        except httpx.HTTPError as e:
            raise APIError(f"Gemini connection error: {e}")

        if response.status_code != 200:
            # Never log the key or full headers
            raise APIError(
                f"Gemini API error (HTTP {response.status_code}): "
                f"{self._extract_error(response)}"
            )

        try:
            return response.json()
        except ValueError as e:
            raise APIError(f"Gemini returned invalid JSON: {e}")

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        """Extract error message from Google error response"""
        try:
            data = response.json()
            return data.get("error", {}).get("message", "unknown error")
        except Exception:
            return "unparseable error response"

    @staticmethod
    def _extract_text(data: Dict[str, Any]) -> str:
        """Extract text from candidates response, raising on block/empty"""
        candidates = data.get("candidates") or []
        if not candidates:
            # e.g. prompt blocked by safety filters
            feedback = data.get("promptFeedback", {})
            block_reason = feedback.get("blockReason")
            if block_reason:
                raise APIError(f"Gemini blocked the request: {block_reason}")
            raise APIError("Gemini returned no candidates")

        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if "text" in part)

        if not text.strip():
            raise APIError(
                f"Gemini returned empty text (finishReason={finish_reason})"
            )
        return text

    def generate(self, prompt: str, model: str = None, timeout: int = None,
                 temperature: float = None, system: str = None, **kwargs) -> str:
        """Generate text response"""
        payload = self._build_payload(prompt, json_mode=False,
                                      temperature=temperature, system=system)
        data = self._post(payload, model=model, timeout=timeout)
        return self._extract_text(data)

    def generate_structured(self, prompt: str, schema: Dict[str, Any] = None,
                            model: str = None, timeout: int = None,
                            temperature: float = None, system: str = None,
                            **kwargs) -> Dict[str, Any]:
        """Generate JSON structured response"""
        payload = self._build_payload(prompt, json_mode=True,
                                      temperature=temperature, system=system)
        if schema:
            payload["generationConfig"]["responseSchema"] = schema

        data = self._post(payload, model=model, timeout=timeout)
        text = self._extract_text(data)
        parsed = self._safe_json_parse(text)
        if not parsed:
            raise APIError("Gemini returned unparseable JSON")
        return parsed