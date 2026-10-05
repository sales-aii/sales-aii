# -*- coding: utf-8 -*-
"""
Conversation repository
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from database.models import Conversation


class ConversationRepository(BaseRepository[Conversation]):
    """Conversation repository"""

    def __init__(self):
        super().__init__(Conversation)

    def get_by_lead_id(self, session: Session, lead_id: int) -> List[Conversation]:
        """Get conversations by lead"""
        return session.query(Conversation).filter(Conversation.lead_id == lead_id).all()

    def get_active_by_lead(self, session: Session,
                           lead_id: int) -> Optional[Conversation]:
        """
        Get the open conversation of a lead, if any.

        Used so a lead is never given two parallel active conversations.
        """
        return (
            session.query(Conversation)
            .filter(
                Conversation.lead_id == lead_id,
                Conversation.status == 'active',
            )
            .order_by(Conversation.id.desc())
            .first()
        )

    def get_by_status(self, session: Session, status: str) -> List[Conversation]:
        """Get conversations by status"""
        return session.query(Conversation).filter(Conversation.status == status).all()
