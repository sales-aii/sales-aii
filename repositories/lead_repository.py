# -*- coding: utf-8 -*-
"""
Lead repository
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from database.models import Lead


class LeadRepository(BaseRepository[Lead]):
    """Lead repository"""

    def __init__(self):
        super().__init__(Lead)

    def get_by_username_and_platform(self, session: Session, username: str, platform: str) -> Optional[Lead]:
        """Get lead by username and platform (for duplicate check)"""
        return session.query(Lead).filter(
            Lead.username == username,
            Lead.platform == platform
        ).first()

    def get_by_source_url(self, session: Session, source_url: str) -> Optional[Lead]:
        """Get lead by its source post/issue URL (primary duplicate check)"""
        return session.query(Lead).filter(Lead.source_url == source_url).first()

    def get_by_platform_and_id(self, session: Session, platform: str,
                               platform_id: str) -> Optional[Lead]:
        """Get lead by platform + platform specific id"""
        return session.query(Lead).filter(
            Lead.platform == platform,
            Lead.platform_id == platform_id
        ).first()

    def get_by_platform(self, session: Session, platform: str) -> List[Lead]:
        """Get leads by platform"""
        return session.query(Lead).filter(Lead.platform == platform).all()

    def get_by_status(self, session: Session, status: str) -> List[Lead]:
        """Get leads by status"""
        return session.query(Lead).filter(Lead.status == status).all()

    def exists(self, session: Session, username: str, platform: str) -> bool:
        """Check if lead exists"""
        return self.get_by_username_and_platform(session, username, platform) is not None
