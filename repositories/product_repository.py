# -*- coding: utf-8 -*-
"""
Product repository
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from database.models import Product


class ProductRepository(BaseRepository[Product]):
    """Product repository"""

    def __init__(self):
        super().__init__(Product)

    def get_by_name(self, session: Session, name: str) -> Optional[Product]:
        """Get product by name"""
        return session.query(Product).filter(Product.name == name).first()

    def get_active(self, session: Session) -> List[Product]:
        """Get active products"""
        return session.query(Product).filter(Product.active == True).all()

    def exists_by_name(self, session: Session, name: str) -> bool:
        """Check if product exists by name"""
        return session.query(Product).filter(Product.name == name).count() > 0
