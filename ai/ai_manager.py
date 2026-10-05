# -*- coding: utf-8 -*-
"""
AI Manager - AI provider system
"""

import time
from typing import Optional, Dict, Any, List
from utils.logger import logger
from utils.exceptions import APIError
from config.config import settings
from ai.providers.mock_provider import MockProvider
from ai.providers.gemini_provider import GeminiProvider


class AIManager:
    """
    AI Provider management system - centralized
    """

    def __init__(self):
        self.logger = logger
        self.providers = {}
        self.active_provider = None
        self.initialize_providers()

    def initialize_providers(self):
        """Initialize available AI providers"""
        self.logger.info("Initializing AI providers")

        # Real providers - registered only when configured
        self._register_gemini()

        # Mock provider always available (fallback / testing)
        self.register_provider(MockProvider())

        # Pick active provider
        configured = settings.AI_PROVIDER.lower()
        if configured in self.providers and configured != 'mock':
            self.active_provider = configured
            self.logger.info(f"Active AI provider: {configured} (model={settings.GEMINI_MODEL})")
        else:
            if configured != 'mock':
                self.logger.warning(
                    f"AI_PROVIDER '{settings.AI_PROVIDER}' not available - "
                    "falling back to mock (no API key configured?)"
                )
            self.active_provider = 'mock'

    def _register_gemini(self):
        """Register Gemini provider if API key is configured"""
        try:
            provider = GeminiProvider(
                timeout=settings.AI_TIMEOUT,
                max_retries=settings.AI_MAX_RETRIES
            )
            if provider.is_configured():
                self.providers['gemini'] = provider
                self.logger.info("Gemini provider registered")
            else:
                self.logger.info("Gemini API key not set - provider disabled")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini provider: {e}")

    def register_provider(self, provider):
        """Register a provider"""
        self.providers[provider.name] = provider
        if not self.active_provider:
            self.active_provider = provider.name

    def get_provider(self, provider_name: str = None):
        """Get specific AI provider"""
        name = provider_name or self.active_provider
        if name not in self.providers:
            self.logger.warning(f"Provider '{name}' not available, using mock")
            return self.providers.get('mock')
        return self.providers[name]

    def is_real_provider_active(self) -> bool:
        """True if a real (non-mock) provider is currently active"""
        return self.active_provider in self.providers and self.active_provider != 'mock'

    def set_active_provider(self, provider_name: str):
        """Set active provider"""
        if provider_name in self.providers:
            self.active_provider = provider_name
            return True
        return False

    def generate_response(self, prompt: str, provider: Optional[str] = None,
                          max_retries: int = None, timeout: int = None, **kwargs) -> str:
        """Generate AI response with retry and timeout handling"""
        provider_instance = self.get_provider(provider)
        retries = 0
        last_error = None
        max_retries = max_retries or settings.AI_MAX_RETRIES
        timeout = timeout or settings.AI_TIMEOUT

        while retries < max_retries:
            try:
                response = provider_instance.generate(prompt, timeout=timeout, **kwargs)
                return response
            except Exception as e:
                last_error = e
                retries += 1
                self.logger.warning(
                    f"AI attempt {retries}/{max_retries} failed "
                    f"(provider={provider_instance.name}): {e}"
                )
                if retries < max_retries:
                    time.sleep(retries * 0.5)  # Exponential backoff
        self.logger.error(f"All {max_retries} attempts failed")
        raise APIError(f"AI generation failed: {last_error}")

    def generate_structured_response(self, prompt: str, schema: Dict[str, Any] = None,
                                   provider: Optional[str] = None,
                                   strict: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Generate structured JSON response.

        strict=True (default) raises APIError on failure so failures are never
        silently reported as an empty-but-valid result.
        """
        provider_instance = self.get_provider(provider)
        try:
            result = provider_instance.generate_structured(
                prompt,
                schema=schema,
                timeout=settings.AI_TIMEOUT,
                **kwargs
            )
            if not result:
                raise APIError("AI returned empty structured response")
            return result
        except Exception as e:
            self.logger.error(
                f"Structured generation failed (provider={provider_instance.name}): {e}"
            )
            if strict:
                raise APIError(f"Structured AI generation failed: {e}")
            return {}

    def is_configured(self) -> bool:
        """Check if any AI provider is configured"""
        return len(self.providers) > 0

    def is_configured_with_real_keys(self) -> bool:
        """Check if any real provider is configured (not mock)"""
        return any([
            settings.OPENAI_API_KEY,
            settings.ANTHROPIC_API_KEY,
            settings.GEMINI_API_KEY
        ])

    def get_active_model(self) -> str:
        """Get active model id (mock if no real provider)"""
        provider = self.get_provider()
        return getattr(provider, 'model', 'mock')

    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return list(self.providers.keys())

    def validate_offer(self, product_min_price: float = None, 
                     suggested_discount: float = None,
                     original_price: float = None) -> Dict[str, Any]:
        """
        Validate AI suggestions for offers - enforce business rules
        - AI cannot suggest discount > 60%
        - AI cannot suggest price below minimum price
        - Final offer/payment decisions validated by backend
        """
        result = {"valid": True, "warnings": [], "adjustments": []}
        
        if suggested_discount is not None:
            if suggested_discount > 60:
                result["valid"] = False
                result["warnings"].append(f"Discount {suggested_discount}% exceeds max 60%")
        
        if product_min_price is not None and original_price is not None:
            min_discounted = original_price * (1 - suggested_discount / 100) if suggested_discount else original_price
            if min_discounted < product_min_price:
                result["valid"] = False
                result["warnings"].append(f"Price below minimum {product_min_price}")
        
        return result
