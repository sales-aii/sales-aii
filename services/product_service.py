# -*- coding: utf-8 -*-
"""
Product service
"""

from typing import Optional, List
from services.base_service import BaseService
from repositories.product_repository import ProductRepository
from repositories.discount_code_repository import DiscountCodeRepository


class ProductService(BaseService):
    """Product service with business logic"""

    def __init__(self):
        super().__init__()
        self.repo = ProductRepository()
        self.discount_repo = DiscountCodeRepository()

    def create_product(self, name: str, description: str = None,
                      normal_price: float = None, minimum_price: float = None,
                      shopier_url: str = None, active: bool = True,
                      discount_codes: List[dict] = None) -> Optional[dict]:
        """Create product with duplicate check"""
        try:
            with self.db.session_scope() as session:
                # Duplicate check
                if self.repo.exists_by_name(session, name):
                    self.logger.warning(f"Product already exists: {name}")
                    return None
                product = self.repo.create(
                    session,
                    name=name,
                    description=description,
                    normal_price=normal_price,
                    minimum_price=minimum_price,
                    shopier_url=shopier_url,
                    active=active
                )
                
                # Add discount codes if provided
                if discount_codes:
                    for dc in discount_codes:
                        self.discount_repo.create(
                            session,
                            product_id=product.id,
                            code=dc['code'],
                            discount_percent=dc['discount_percent'],
                            active=dc.get('active', True),
                            description=dc.get('description'),
                            difficulty=dc.get('difficulty')
                        )
                
                return {
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "normal_price": float(product.normal_price) if product.normal_price else None,
                    "minimum_price": float(product.minimum_price) if product.minimum_price else None,
                    "shopier_url": product.shopier_url,
                    "active": product.active
                }
        except Exception as e:
            self.logger.error(f"Error creating product: {e}")
            raise

    def get_product(self, product_id: int) -> Optional[dict]:
        """Get product"""
        try:
            with self.db.session_scope() as session:
                product = self.repo.get_by_id(session, product_id)
                if not product:
                    return None
                return {
                    "id": product.id,
                    "name": product.name,
                    "description": product.description,
                    "normal_price": float(product.normal_price) if product.normal_price else None,
                    "minimum_price": float(product.minimum_price) if product.minimum_price else None,
                    "shopier_url": product.shopier_url,
                    "active": product.active
                }
        except Exception as e:
            self.logger.error(f"Error getting product: {e}")
            return None

    def get_all_products(self) -> List[dict]:
        """Get all products"""
        try:
            with self.db.session_scope() as session:
                products = self.repo.get_all(session)
                return [{
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "normal_price": float(p.normal_price) if p.normal_price else None,
                    "minimum_price": float(p.minimum_price) if p.minimum_price else None,
                    "shopier_url": p.shopier_url,
                    "active": p.active
                } for p in products]
        except Exception as e:
            self.logger.error(f"Error getting products: {e}")
            return []

    def get_active_products(self) -> List[dict]:
        """Get active products"""
        try:
            with self.db.session_scope() as session:
                products = self.repo.get_active(session)
                return [{
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "normal_price": float(p.normal_price) if p.normal_price else None,
                    "minimum_price": float(p.minimum_price) if p.minimum_price else None,
                    "shopier_url": p.shopier_url,
                    "active": p.active
                } for p in products]
        except Exception as e:
            self.logger.error(f"Error getting active products: {e}")
            return []

    def update_product(self, product_id: int, **kwargs) -> bool:
        """Update product"""
        try:
            with self.db.session_scope() as session:
                product = self.repo.get_by_id(session, product_id)
                if not product:
                    return False
                self.repo.update(session, product, **kwargs)
                return True
        except Exception as e:
            self.logger.error(f"Error updating product: {e}")
            return False

    def delete_product(self, product_id: int) -> bool:
        """Delete product"""
        try:
            with self.db.session_scope() as session:
                return self.repo.delete_by_id(session, product_id)
        except Exception as e:
            self.logger.error(f"Error deleting product: {e}")
            return False

    def get_discount_codes(self, product_id: int, active_only: bool = True) -> List[dict]:
        """Get discount codes for product"""
        try:
            with self.db.session_scope() as session:
                if active_only:
                    codes = self.discount_repo.get_active_by_product(session, product_id)
                else:
                    codes = self.discount_repo.get_by_product(session, product_id)
                return [{
                    "id": c.id,
                    "code": c.code,
                    "discount_percent": c.discount_percent,
                    "active": c.active,
                    "difficulty": c.difficulty,
                    "description": c.description
                } for c in codes]
        except Exception as e:
            self.logger.error(f"Error getting discount codes: {e}")
            return []

    def add_discount_code(self, product_id: int, code: str, discount_percent: float, 
                         active: bool = True, description: str = None) -> Optional[dict]:
        """Add discount code to product"""
        try:
            with self.db.session_scope() as session:
                if self.discount_repo.exists(session, code, product_id):
                    return None
                dc = self.discount_repo.create(
                    session,
                    product_id=product_id,
                    code=code,
                    discount_percent=discount_percent,
                    active=active,
                    description=description,
                    difficulty=self._calc_diff(discount_percent)
                )
                return {
                    "id": dc.id,
                    "code": dc.code,
                    "discount_percent": dc.discount_percent
                }
        except Exception as e:
            self.logger.error(f"Error adding discount code: {e}")
            return None

    def _calc_diff(self, percent: float) -> str:
        if percent <= 20:
            return "easy"
        elif percent <= 30:
            return "normal"
        elif percent <= 40:
            return "hard"
        elif percent <= 60:
            return "very_hard"
        return "impossible"
