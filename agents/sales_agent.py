# -*- coding: utf-8 -*-
"""
Sales Agent - Sales conversations and negotiations
"""

from typing import Dict, Any
from services.base_service import BaseService
from services.lead_service import LeadService
from services.product_service import ProductService
from services.discount_engine import DiscountEngine
from services.message_service import MessageService
from ai.ai_manager import AIManager
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository
from repositories.offer_repository import OfferRepository
from utils.exceptions import APIError


class SalesAgent(BaseService):
    """
    Sales Agent responsible for:
    - Sales conversations
    - Negotiation
    - Follow-up
    """

    def __init__(self):
        super().__init__()
        self.agent_type = "sales"
        self.lead_service = LeadService()
        self.product_service = ProductService()
        self.discount_engine = DiscountEngine()
        self.message_service = MessageService()
        self.ai_manager = AIManager()
        self.conv_repo = ConversationRepository()
        self.msg_repo = MessageRepository()
        self.offer_repo = OfferRepository()

    def start_conversation(self, lead_id: int) -> Dict[str, Any]:
        """Start sales conversation with lead"""
        self.logger.info(f"Starting sales conversation with lead {lead_id}")
        lead = self.lead_service.get_lead(lead_id)
        if not lead:
            raise APIError(f"SalesAgent: lead {lead_id} not found")
        with self.db.session_scope() as session:
            existing = self.conv_repo.get_active_by_lead(session, lead_id)
            if existing:
                self.logger.info(
                    f"Reusing active conversation {existing.id} for lead {lead_id}"
                )
                return {'conversation_id': existing.id, 'reused': True}
            conv = self.conv_repo.create(
                session,
                lead_id=lead_id,
                platform=lead['platform'],
                status='active'
            )
            return {'conversation_id': conv.id, 'reused': False}

    def draft_first_message(self, lead_id: int, conversation_id: int) -> Dict[str, Any]:
        """
        Draft the first sales message.

        The draft is stored unapproved and unsent; sending requires an explicit
        user action. Raises APIError when the AI call fails.
        """
        lead = self.lead_service.get_lead(lead_id)
        if not lead:
            raise APIError(f"SalesAgent: lead {lead_id} not found")
        products = self.product_service.get_active_products()
        context = {
            'lead': {
                'need': lead.get('need'),
                'need_description': lead.get('need_description')
            },
            'products': products[:2] if products else []
        }
        prompt = (
            "Draft a FIRST sales message. Keep it SHORT, NATURAL, specific to "
            "need. NO spam, NO aggressive sales pressure. Reply with ONLY JSON.\n"
            f"Context: {context}\n"
            "Keys: intent, interest_level (low/medium/high), "
            "price_objection (true/false), buying_signal (low/medium/high), "
            "recommended_action, draft_message, "
            "recommended_discount_level (0-60)."
        )
        result = self.ai_manager.generate_structured_response(prompt)
        draft_message = result.get('draft_message')
        if not draft_message:
            raise APIError("SalesAgent: AI did not return a draft_message")

        message = self.message_service.create_draft(
            conversation_id, draft_message, sender='agent'
        )
        if message is None:
            raise APIError("SalesAgent: failed to store the drafted message")
        result['message_id'] = message['id']
        result['approved'] = False
        result['sent'] = False
        return result

    def approve_and_send(self, conversation_id: int, message_id: int,
                         approved: bool = True) -> Dict[str, Any]:
        """
        Approve (or reject) a draft and send it.

        Sending goes through MessageService, which is the only place allowed to
        mark a message as sent - and only when a real channel delivered it.
        """
        if not self._message_in_conversation(message_id, conversation_id):
            return {
                'success': False,
                'error': f'Message {message_id} does not belong to '
                         f'conversation {conversation_id}'
            }
        if not approved:
            return self.message_service.reject(message_id)
        return self.message_service.approve_and_send(message_id)

    def _message_in_conversation(self, message_id: int,
                                 conversation_id: int) -> bool:
        with self.db.session_scope() as session:
            msg = self.msg_repo.get_by_id(session, message_id)
            return bool(msg and msg.conversation_id == conversation_id)

    def process_customer_reply(self, conversation_id: int,
                               customer_message: str) -> Dict[str, Any]:
        """Process customer reply - save, analyze, draft reply"""
        if not customer_message or not customer_message.strip():
            raise APIError("SalesAgent: customer_message cannot be empty")
        with self.db.session_scope() as session:
            self.msg_repo.create(
                session,
                conversation_id=conversation_id,
                sender='user',
                content=customer_message,
                message_type='text',
                status='sent',
                approved=True,
                sent=True
            )
        analysis = self.analyze_reply(conversation_id, customer_message)
        draft = self.draft_reply(conversation_id, customer_message, analysis)
        return {'analysis': analysis, 'draft': draft}

    def analyze_reply(self, conversation_id: int, message: str) -> Dict[str, Any]:
        """Analyze a customer message (raises APIError on AI failure)"""
        prompt = (
            "Analyze customer message. Reply with ONLY JSON.\n"
            f"Message: {message}\n"
            "Keys: intent, interest_level (low/medium/high), "
            "price_objection (true/false), buying_signal (low/medium/high), "
            "recommended_action, recommended_discount_level (0-60)"
        )
        return self.ai_manager.generate_structured_response(prompt)

    def draft_reply(self, conversation_id: int, customer_message: str,
                    analysis: Dict = None) -> Dict[str, Any]:
        """Draft a reply and store it as an unapproved draft"""
        prompt = (
            "Draft appropriate reply to customer. Natural, helpful, not pushy. "
            "Reply with ONLY JSON.\n"
            f"Customer: {customer_message}\n"
            f"Analysis: {analysis or {}}\n"
            "Keys: draft_message, recommended_action"
        )
        result = self.ai_manager.generate_structured_response(prompt)
        draft_message = result.get('draft_message')
        if draft_message:
            message = self.message_service.create_draft(
                conversation_id, draft_message, sender='agent'
            )
            result['message_id'] = message['id'] if message else None
            result['approved'] = False
            result['sent'] = False
        return result

    def negotiate(self, conversation_id: int, product_id: int = None,
                  proposed_discount: float = None,
                  discount_code: str = None) -> Dict[str, Any]:
        """Handle negotiation with discount engine validation (backend enforced)"""
        if not product_id:
            return {'success': False, 'error': 'product_id required'}
        has_final = self._has_final_offer(conversation_id)
        validation = self.discount_engine.validate_discount(
            product_id=product_id,
            discount_percent=proposed_discount or 0,
            discount_code=discount_code,
            has_final_offer=has_final
        )
        if not validation['valid']:
            self.logger.info(
                f"Negotiation rejected for product {product_id}: "
                f"{validation['errors']}"
            )
            return {'success': False, 'errors': validation['errors']}
        if proposed_discount is not None:
            with self.db.session_scope() as session:
                self.offer_repo.create(
                    session,
                    conversation_id=conversation_id,
                    product_id=product_id,
                    discount_percent=proposed_discount,
                    discount_code=discount_code,
                    original_price=validation['original_price'],
                    final_price=validation['final_price'],
                    is_final_offer=validation.get('is_final_offer', False)
                )
        return {'success': True, 'validation': validation}

    def _has_final_offer(self, conversation_id: int) -> bool:
        try:
            with self.db.session_scope() as session:
                return self.offer_repo.has_final_offer(session, conversation_id)
        except Exception as e:
            # Failing to read the offer history must not silently unlock
            # discounts, so report the problem loudly.
            self.logger.error(
                f"Could not read final offer history for conversation "
                f"{conversation_id}: {e}"
            )
            raise APIError(
                f"SalesAgent: could not verify final offer state: {e}"
            )

    def follow_up(self, lead_id: int) -> Dict[str, Any]:
        """Suggest a follow-up approach - suggestion only, never sent"""
        lead = self.lead_service.get_lead(lead_id)
        if not lead:
            raise APIError(f"SalesAgent: lead {lead_id} not found")
        prompt = (
            "Suggest a follow-up approach. Reply with ONLY JSON.\n"
            f"Lead: {lead}\n"
            "Keys: should_follow_up (true/false), timing (hours/days), "
            "draft_message (suggested), reason"
        )
        return self.ai_manager.generate_structured_response(prompt)
