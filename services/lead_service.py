# -*- coding: utf-8 -*-
"""
Lead service
"""

from typing import Optional, List
from services.base_service import BaseService
from repositories.lead_repository import LeadRepository


class LeadService(BaseService):
    """Lead service"""

    def __init__(self):
        super().__init__()
        self.repo = LeadRepository()

    def create_lead(self, platform: str, username: str, **kwargs) -> Optional[dict]:
        """
        Create a lead, returning the existing row when it is a duplicate.

        Duplicate detection prefers the most specific key available:
        source_url -> platform + platform_id -> platform + username.
        A single user may raise several distinct needs, so username alone is
        only used when nothing better exists.
        """
        try:
            source_url = kwargs.get('source_url')
            platform_id = kwargs.get('platform_id')

            with self.db.session_scope() as session:
                existing = None
                if source_url:
                    existing = self.repo.get_by_source_url(session, source_url)
                if existing is None and platform_id:
                    existing = self.repo.get_by_platform_and_id(
                        session, platform, str(platform_id)
                    )
                if existing is None and username and not (source_url or platform_id):
                    existing = self.repo.get_by_username_and_platform(
                        session, username, platform
                    )

                if existing is not None:
                    self.logger.info(
                        f"Lead already exists: {platform}:"
                        f"{source_url or platform_id or username}"
                    )
                    return {
                        "id": existing.id,
                        "platform": existing.platform,
                        "username": existing.username,
                        "status": existing.status
                    }

                lead = self.repo.create(
                    session,
                    platform=platform,
                    username=username,
                    **kwargs
                )
                return {
                    "id": lead.id,
                    "platform": lead.platform,
                    "username": lead.username,
                    "profile_url": lead.profile_url,
                    "source_url": lead.source_url,
                    "need": lead.need,
                    "need_description": lead.need_description,
                    "suggested_product_id": lead.suggested_product_id,
                    "lead_quality": lead.lead_quality,
                    "status": lead.status
                }
        except Exception as e:
            self.logger.error(f"Error creating lead: {e}")
            raise

    def get_lead(self, lead_id: int) -> Optional[dict]:
        """Get lead"""
        try:
            with self.db.session_scope() as session:
                lead = self.repo.get_by_id(session, lead_id)
                if not lead:
                    return None
                return {
                    "id": lead.id,
                    "platform": lead.platform,
                    "username": lead.username,
                    "need": lead.need,
                    "need_description": lead.need_description,
                    "status": lead.status,
                    "lead_quality": lead.lead_quality,
                    "suggested_product_id": lead.suggested_product_id
                }
        except Exception as e:
            self.logger.error(f"Error getting lead: {e}")
            return None

    def get_all_leads(self) -> List[dict]:
        """Get all leads"""
        try:
            with self.db.session_scope() as session:
                leads = self.repo.get_all(session)
                return [{
                    "id": l.id,
                    "platform": l.platform,
                    "username": l.username,
                    "need": l.need,
                    "status": l.status,
                    "lead_quality": l.lead_quality,
                    "created_at": l.created_at
                } for l in leads]
        except Exception as e:
            self.logger.error(f"Error getting leads: {e}")
            return []

    def update_lead(self, lead_id: int, **kwargs) -> bool:
        """Update lead"""
        try:
            with self.db.session_scope() as session:
                lead = self.repo.get_by_id(session, lead_id)
                if not lead:
                    return False
                self.repo.update(session, lead, **kwargs)
                return True
        except Exception as e:
            self.logger.error(f"Error updating lead: {e}")
            return False

    def delete_lead(self, lead_id: int) -> bool:
        """Delete lead"""
        try:
            with self.db.session_scope() as session:
                return self.repo.delete_by_id(session, lead_id)
        except Exception as e:
            self.logger.error(f"Error deleting lead: {e}")
            return False
