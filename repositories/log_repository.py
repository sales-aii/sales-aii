# -*- coding: utf-8 -*-
"""
Log repository
"""

from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from database.models import Log


class LogRepository(BaseRepository[Log]):
    """Log repository"""

    def __init__(self):
        super().__init__(Log)

    def get_by_level(self, session: Session, level: str):
        """Get logs by level"""
        return session.query(Log).filter(Log.level == level).order_by(Log.created_at.desc()).all()

    def get_recent(self, session: Session, limit: int = 50):
        """Get recent logs"""
        return session.query(Log).order_by(Log.created_at.desc()).limit(limit).all()
