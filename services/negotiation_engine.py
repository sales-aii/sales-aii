# -*- coding: utf-8 -*-
"""
Negotiation Engine
"""

from typing import Dict, Any
from services.base_service import BaseService
from services.discount_engine import DiscountEngine
from utils.exceptions import APIError


class NegotiationEngine(BaseService):
    """
    Negotiation logic based on levels and signals
    """

    def __init__(self):
        super().__init__()
        self.discount_engine = DiscountEngine()

    def determine_discount(self, buying_signal: str, price_objection: bool,
                          lead_quality: str = None, interest_level: str = None) -> float:
        """
        Determine appropriate discount level based on signals
        """
        buying_signal = (buying_signal or '').lower()
        lead_quality = (lead_quality or '').lower()
        interest_level = (interest_level or '').lower()

        # Strong signals
        strong_signals = [
            'almak istiyorum ama',
            'şu fiyata olursa alırım',
            'indirim olursa hemen alırım',
            'bütçem şu kadar',
            'want to buy but',
            'if discount then buy',
            'can buy at this price',
            'my budget'
        ]

        # Weak signals
        weak_signals = [
            'pahalı',
            'düşüneyim',
            'başka yerlere bakacağım',
            'expensive',
            'i need to think',
            'look elsewhere'
        ]

        # If strong signal exists, can go higher appropriately
        has_strong = any(s in buying_signal for s in strong_signals)
        has_weak = any(s in buying_signal for s in weak_signals)

        # Default logic
        if has_weak:
            # Zayıf sinyal nedeniyle doğrudan %40 veya %60 verme
            return 10  # Start low

        if has_strong and price_objection:
            if lead_quality == 'high':
                return 40  # %40 için güçlü satın alma niyeti gerekir (high quality + strong)
            return 30

        if price_objection:
            if interest_level == 'high':
                return 20
            return 10

        if buying_signal == 'high' or interest_level == 'high':
            return 10

        return 0

    def negotiate_step(self, product_id: int, conversation_id: int,
                      buying_signal: str, price_objection: bool,
                      proposed_discount: float = None) -> Dict[str, Any]:
        """Execute negotiation step with validation"""
        if proposed_discount is None:
            proposed_discount = self.determine_discount(buying_signal, price_objection)

        # Use discount engine validation
        has_final = self._has_final_offer(conversation_id)
        validation = self.discount_engine.validate_discount(
            product_id=product_id,
            discount_percent=proposed_discount,
            has_final_offer=has_final
        )

        if not validation['valid']:
            return {
                'success': False,
                'proposed_discount': proposed_discount,
                'errors': validation['errors']
            }

        return {
            'success': True,
            'proposed_discount': proposed_discount,
            'is_final_offer': validation.get('is_final_offer', False),
            'final_price': validation.get('final_price'),
            'difficulty': validation.get('difficulty'),
            'validation': validation
        }

    def _has_final_offer(self, conversation_id: int) -> bool:
        from repositories.offer_repository import OfferRepository
        repo = OfferRepository()
        try:
            with self.db.session_scope() as session:
                return repo.has_final_offer(session, conversation_id)
        except Exception as e:
            # Failing to read the offer history must not silently unlock
            # discounts, so the problem is reported instead.
            self.logger.error(
                f"Could not read final offer history for conversation "
                f"{conversation_id}: {e}"
            )
            raise APIError(
                f"NegotiationEngine: could not verify final offer state: {e}"
            ) from e
