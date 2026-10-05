# -*- coding: utf-8 -*-
"""
Mock AI Provider for offline testing.

The mock must always return schema-valid JSON for structured calls, otherwise
a test would pass only because failures were being swallowed. Responses are
selected from the prompt so agent code paths can be exercised end to end.
"""

import json
from typing import Any, Dict

from ai.providers.base_provider import BaseAIProvider


class MockProvider(BaseAIProvider):
    """Mock provider for testing without real API keys"""

    #: Valid JSON answers per detected intent
    STRUCTURED_RESPONSES = {
        "analysis": {
            "need": "Mock analyzed need",
            "need_description": "Mock analyzed description",
            "product_match": None,
            "buying_intent": "medium",
            "lead_quality": "Medium",
            "analysis": "positive",
            "score": 8,
            "sentiment": "positive",
        },
        "offer": {
            "discount_percent": 10,
            "offered_discount": 10,
            "final_price": 90,
            "message": "We can offer 10% discount",
            "draft_message": "We can offer 10% discount",
            "reasoning": "Mock negotiation reasoning",
            "is_final_offer": False,
        },
        "draft": {
            "intent": "question",
            "interest_level": "medium",
            "price_objection": False,
            "buying_signal": "medium",
            "recommended_action": "answer",
            "draft_message": "Mock drafted message",
            "recommended_discount_level": 0,
        },
        "insights": {
            "summary": "Mock summary",
            "recommendations": ["Mock recommendation"],
            "insights": [],
        },
    }

    def __init__(self, **kwargs):
        super().__init__('mock', **kwargs)
        self.responses = {
            'default': 'Mock response',
            'analysis': json.dumps(self.STRUCTURED_RESPONSES['analysis']),
            'offer': json.dumps(self.STRUCTURED_RESPONSES['offer']),
            'draft': json.dumps(self.STRUCTURED_RESPONSES['draft']),
        }

    def is_configured(self) -> bool:
        """Always configured for testing"""
        return True

    @staticmethod
    def _detect_intent(prompt: str) -> str:
        """
        Pick the intent that matches the prompt.

        Order matters and must stay narrow: prompts frequently contain the word
        "recommended_action", so a loose 'recommend' match would wrongly route
        a drafting prompt to the insights response.
        """
        text = (prompt or "").lower()
        if any(k in text for k in ('offer', 'discount', 'negotiat')):
            return "offer"
        if 'draft' in text or any(k in text for k in ('reply', 'respond')):
            return "draft"
        if any(k in text for k in ('analyz', 'lead', 'qualif')):
            return "analysis"
        if any(k in text for k in ('insight', 'dashboard')):
            return "insights"
        return "analysis"

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate a mock text response"""
        intent = self._detect_intent(prompt)
        return self.responses.get(intent, self.responses['default'])

    def generate_structured(self, prompt: str, schema: Dict[str, Any] = None,
                            **kwargs) -> Dict[str, Any]:
        """
        Generate a mock structured response.

        Always returns a dict - a structured call that yields nothing would be
        indistinguishable from a provider failure.
        """
        intent = self._detect_intent(prompt)
        return dict(self.STRUCTURED_RESPONSES.get(
            intent, self.STRUCTURED_RESPONSES['analysis']
        ))