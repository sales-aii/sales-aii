# -*- coding: utf-8 -*-
"""
Base AI Provider
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from utils.logger import logger


class BaseAIProvider(ABC):
    """Base class for AI providers"""

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.logger = logger
        self.timeout = kwargs.get('timeout', 60)
        self.max_retries = kwargs.get('max_retries', 3)

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is configured with API key"""
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response"""
        pass

    @abstractmethod
    def generate_structured(self, prompt: str, schema: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Generate structured JSON response"""
        pass

    def _safe_json_parse(self, text: str) -> Dict[str, Any]:
        """Safely parse JSON from response"""
        import json
        try:
            # Try to extract JSON from text
            text = text.strip()
            # If wrapped in markdown code blocks
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            # Find first { and last }
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                text = text[start:end]
            return json.loads(text)
        except Exception as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return {}
