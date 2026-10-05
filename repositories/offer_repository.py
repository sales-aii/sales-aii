# -*- coding: utf-8 -*-
"""
Offer repository
"""

from typing import List
from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from database.models import Offer


class OfferRepository(BaseRepository[Offer]):
    """Offer repository"""

    def __init__(self):
        super().__init__(Offer)

    def get_by_conversation_id(self, session: Session, conversation_id: int) -> List[Offer]:
        """Get offers by conversation"""
        return session.query(Offer).filter(
            Offer.conversation_id == conversation_id
        ).order_by(Offer.created_at.desc()).all()

    def get_final_offer(self, session: Session, conversation_id: int) -> List[Offer]:
        """Get final offers"""
        return session.query(Offer).filter(
            Offer.conversation_id == conversation_id,
            Offer.is_final_offer == True
        ).all()

    def has_final_offer(self, session: Session, conversation_id: int) -> bool:
        """
        Whether this conversation already used its %60 final offer.

        Single source of truth for the "no discount after the final offer" rule,
        so callers cannot disagree about the negotiation state.
        """
        return (
            session.query(Offer.id)
            .filter(
                Offer.conversation_id == conversation_id,
                Offer.is_final_offer == True
            )
            .first()
            is not None
        )
