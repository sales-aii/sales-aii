# -*- coding: utf-8 -*-
"""
Base repository
"""

from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.orm import Session
from database.database import db

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository class"""

    def __init__(self, model: Type[T]):
        self.model = model
        self.db = db

    def get_by_id(self, session: Session, id: int) -> Optional[T]:
        """Get entity by ID"""
        return session.query(self.model).filter(self.model.id == id).first()

    def get_all(self, session: Session) -> List[T]:
        """Get all entities"""
        return session.query(self.model).all()

    def get_all_paginated(self, session: Session, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with pagination"""
        return session.query(self.model).offset(offset).limit(limit).all()

    def count(self, session: Session) -> int:
        """Count entities"""
        return session.query(self.model).count()

    def create(self, session: Session, **kwargs) -> T:
        """Create entity"""
        entity = self.model(**kwargs)
        session.add(entity)
        session.flush()
        return entity

    def update(self, session: Session, entity: T, **kwargs) -> T:
        """Update entity"""
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        session.flush()
        return entity

    def delete(self, session: Session, entity: T) -> bool:
        """Delete entity"""
        try:
            session.delete(entity)
            session.flush()
            return True
        except Exception:
            return False

    def delete_by_id(self, session: Session, id: int) -> bool:
        """Delete entity by ID"""
        entity = self.get_by_id(session, id)
        if entity:
            return self.delete(session, entity)
        return False
