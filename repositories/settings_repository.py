# -*- coding: utf-8 -*-
"""
Settings repository
"""

from typing import Optional
from sqlalchemy.orm import Session
from database.models import Settings


class SettingsRepository:
    """Settings repository (key/value store, not a BaseRepository entity)"""

    def __init__(self):
        self.model = Settings

    def get(self, session: Session, key: str) -> Optional[Settings]:
        """Get setting by key"""
        return session.query(Settings).filter(Settings.key == key).first()

    def get_value(self, session: Session, key: str, default: str = None) -> Optional[str]:
        """Get setting value by key"""
        setting = self.get(session, key)
        if setting:
            return setting.value
        return default

    def set(self, session: Session, key: str, value: str) -> Settings:
        """Set setting (create or update)"""
        setting = self.get(session, key)
        if setting:
            setting.value = value
            session.flush()
            return setting
        else:
            setting = Settings(key=key, value=value)
            session.add(setting)
            session.flush()
            return setting

    def delete(self, session: Session, key: str) -> bool:
        """Delete setting"""
        setting = self.get(session, key)
        if setting:
            session.delete(setting)
            session.flush()
            return True
        return False

    def get_all(self, session: Session):
        """Get all settings"""
        return session.query(Settings).all()
