# -*- coding: utf-8 -*-
"""
Sale repository
"""

from typing import List
from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from database.models import Sale


class SaleRepository(BaseRepository[Sale]):
    """Sale repository"""

    def __init__(self):
        super().__init__(Sale)

    def get_by_lead_id(self, session: Session, lead_id: int) -> List[Sale]:
        """Get sales by lead"""
        return session.query(Sale).filter(Sale.lead_id == lead_id).all()

    def get_by_payment_status(self, session: Session, status: str) -> List[Sale]:
        """Get sales by payment status"""
        return session.query(Sale).filter(Sale.payment_status == status).all()

    def get_by_shopier_reference(self, session: Session, ref: str) -> List[Sale]:
        """Get sales by shopier reference"""
        return session.query(Sale).filter(Sale.shopier_reference == ref).all()
