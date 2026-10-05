# -*- coding: utf-8 -*-
"""
Support Agent - Post-sale support
"""

from typing import Dict, Any
from services.base_service import BaseService
from services.product_service import ProductService
from ai.ai_manager import AIManager
from utils.exceptions import APIError


class SupportAgent(BaseService):
    """
    Support Agent responsible for:
    - Post-sale support
    - Product usage questions
    - Escalation to owner when unknown
    """

    #: Below this confidence the owner is asked to take over
    CONFIDENCE_THRESHOLD = 0.5

    def __init__(self):
        super().__init__()
        self.agent_type = "support"
        self.product_service = ProductService()
        self.ai_manager = AIManager()

    def handle_ticket(self, ticket_id: int = None, ticket_data: Dict = None) -> Dict[str, Any]:
        """Handle support ticket"""
        self.logger.info(f"Handling support ticket {ticket_id}")
        result = self.process_ticket(ticket_data or {})
        result['ticket_id'] = ticket_id
        return result

    def process_ticket(self, ticket_data: Dict) -> Dict[str, Any]:
        """
        Process support inquiry.

        Escalates to the owner when the AI is unsure or asks for help. Raises
        APIError when the AI call itself fails, because "the AI is unavailable"
        and "the owner should answer" are different situations.
        """
        if not ticket_data:
            raise APIError("SupportAgent: ticket_data is required")

        inquiry = ticket_data.get('inquiry', '')
        product_id = ticket_data.get('product_id')
        if product_id:
            product = self.product_service.get_product(product_id)
            if not product:
                raise APIError(f"SupportAgent: product {product_id} not found")
            products = [product]
        else:
            products = self.product_service.get_active_products()

        prompt = (
            "Process support ticket. If you don't know answer from provided "
            "product info, DO NOT invent. Return ONLY JSON.\n"
            f"Inquiry: {inquiry}\n"
            f"Products: {products[:2]}\n"
            "Keys: category (product_question/usage_issue/other), "
            "needs_owner_intervention (true/false), "
            "owner_intervention_required (true/false), "
            "suggested_response, confidence (0-1)"
        )
        result = self.ai_manager.generate_structured_response(prompt)

        try:
            confidence = float(result.get('confidence', 1))
        except (TypeError, ValueError):
            confidence = 0.0

        if confidence < self.CONFIDENCE_THRESHOLD or result.get(
            'needs_owner_intervention'
        ):
            result['owner_intervention_required'] = True
        else:
            result['owner_intervention_required'] = bool(
                result.get('owner_intervention_required', False)
            )
        result['confidence'] = confidence
        return result
