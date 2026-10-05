# -*- coding: utf-8 -*-
"""
Message repository
"""

from typing import List
from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from database.models import Message


class MessageRepository(BaseRepository[Message]):
    """Message repository"""

    def __init__(self):
        super().__init__(Message)

    def get_by_conversation_id(self, session: Session, conversation_id: int) -> List[Message]:
        """Get messages by conversation"""
        return session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()

    def get_unsent(self, session: Session) -> List[Message]:
        """Get unsent messages"""
        return session.query(Message).filter(Message.sent == False).all()
