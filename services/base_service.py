# -*- coding: utf-8 -*-
"""
Base service class
"""

from utils.logger import logger
from database.database import db


class BaseService:
    """Base service with common functionality"""
    
    def __init__(self):
        self.db = db
        self.logger = logger
    
    def log_activity(self, agent_type: str = None, action: str = "", details: str = "", status: str = "success"):
        """Log activity"""
        try:
            with self.db.session_scope() as session:
                from database.models import ActivityLog
                log = ActivityLog(
                    agent_type=agent_type,
                    action=action,
                    details=details,
                    status=status
                )
                session.add(log)
        except Exception as e:
            self.logger.error(f"Failed to log activity: {e}")
