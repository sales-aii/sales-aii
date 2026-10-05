# -*- coding: utf-8 -*-
"""
Discount code repository
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from database.models import DiscountCode


class DiscountCodeRepository(BaseRepository[DiscountCode]):
    """Discount code repository"""

    def __init__(self):
        super().__init__(DiscountCode)

    def get_by_code(self, session: Session, code: str) -> Optional[DiscountCode]:
        """Get discount code by code"""
        return session.query(DiscountCode).filter(DiscountCode.code == code).first()

    def get_by_product(self, session: Session, product_id: int) -> List[DiscountCode]:
        """Get discount codes for product"""
        return session.query(DiscountCode).filter(DiscountCode.product_id == product_id).all()

    def get_active_by_product(self, session: Session, product_id: int) -> List[DiscountCode]:
        """Get active discount codes for product"""
        return session.query(DiscountCode).filter(
            DiscountCode.product_id == product_id,
            DiscountCode.active == True
        ).order_by(DiscountCode.discount_percent.asc()).all()

    def get_by_code_and_product(self, session: Session, code: str, product_id: int) -> Optional[DiscountCode]:
        """Get discount code by code and product"""
        return session.query(DiscountCode).filter(
            DiscountCode.code == code,
            DiscountCode.product_id == product_id
        ).first()

    def exists(self, session: Session, code: str, product_id: int) -> bool:
        """Check if discount code exists"""
        return self.get_by_code_and_product(session, code, product_id) is not None
