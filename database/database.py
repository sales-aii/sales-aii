# -*- coding: utf-8 -*-
"""
Database connection and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from utils.logger import logger
from config.config import settings
from database.models import Base


class Database:
    """Database manager"""
    
    def __init__(self):
        self._engine = None
        self._sessionmaker = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database connection"""
        try:
            # SQLite connection string
            db_url = f"sqlite:///{settings.DB_PATH}"
            logger.info(f"Initializing database at {settings.DB_PATH}")
            
            self._engine = create_engine(
                db_url,
                echo=False,
                connect_args={"check_same_thread": False}
            )
            self._sessionmaker = sessionmaker(bind=self._engine)
            
            # Create tables
            self.create_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(self._engine)
    
    def get_session(self) -> Session:
        """Get a new session"""
        return self._sessionmaker()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations"""
        session = self._sessionmaker()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            session.close()
    
    def dispose(self):
        """Dispose engine"""
        if self._engine:
            self._engine.dispose()


# Global database instance
db = Database()
