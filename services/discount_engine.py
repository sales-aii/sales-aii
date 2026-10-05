# -*- coding: utf-8 -*-
"""
Discount Engine
"""

from typing import Dict, Any
from services.base_service import BaseService
from repositories.discount_code_repository import DiscountCodeRepository
from repositories.product_repository import ProductRepository


class DiscountEngine(BaseService):
    """
    Discount engine with strict rules:
    - Up to 30%: system can progress
    - 40%: needs strong buying intent
    - 60%: last resort, final offer
    - Cannot go above 60%
    - 60% is final offer - no more discounts after
    - Final price cannot be below minimum price
    - AI cannot create its own discount codes
    - Only active codes in DB
    - Backend validates everything
    """

    def __init__(self):
        super().__init__()
        self.discount_repo = DiscountCodeRepository()
        self.product_repo = ProductRepository()
        self.MAX_DISCOUNT = 60

    def calculate_difficulty(self, discount_percent: float) -> str:
        """Calculate difficulty"""
        if discount_percent <= 10:
            return "easy"
        elif discount_percent <= 20:
            return "easy"
        elif discount_percent <= 30:
            return "normal"
        elif discount_percent <= 40:
            return "hard"
        elif discount_percent <= 60:
            return "very_hard"
        return "impossible"

    def validate_discount(self, product_id: int, discount_percent: float, 
                         discount_code: str = None, has_final_offer: bool = False) -> Dict[str, Any]:
        """
        Validate discount with all rules
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            # always present so callers never need a .get() fallback
            "is_final_offer": False,
        }

        try:
            with self.db.session_scope() as session:
                # Check if already has final offer (60%)
                if has_final_offer:
                    result["valid"] = False
                    result["errors"].append("%60 sonrası başka indirim yoktur")
                    return result

                # Max 60% rule
                if discount_percent > self.MAX_DISCOUNT:
                    result["valid"] = False
                    result["errors"].append(f"%{discount_percent}'tan büyük indirim kesinlikle reddedilir")
                    return result

                # Get product
                product = self.product_repo.get_by_id(session, product_id)
                if not product:
                    result["valid"] = False
                    result["errors"].append("Ürün bulunamadı")
                    return result

                original_price = float(product.normal_price) if product.normal_price else 0
                min_price = float(product.minimum_price) if product.minimum_price else 0

                # Calculate final price
                final_price = original_price * (1 - discount_percent / 100)

                # Check minimum price
                if final_price < min_price:
                    result["valid"] = False
                    result["errors"].append("Final price minimum_price altına düşerse teklif reddedilir")
                    return result

                # If discount code provided, validate it exists and is active
                if discount_code:
                    code = self.discount_repo.get_by_code_and_product(
                        session, discount_code, product_id
                    )
                    if not code or not code.active:
                        result["valid"] = False
                        result["errors"].append("tanımsız code → reject")
                        return result
                    # Code discount should match
                    if code.discount_percent != discount_percent:
                        result["valid"] = False
                        result["errors"].append("İndirim kodu ile indirim yüzdesi uyuşmuyor")
                        return result

                # 60% is final offer
                if discount_percent == 60:
                    result["is_final_offer"] = True
                    result["warnings"].append("%60 final offer'dır")

                # Difficulty notes
                difficulty = self.calculate_difficulty(discount_percent)
                result["difficulty"] = difficulty

                result["original_price"] = original_price
                result["final_price"] = round(final_price, 2)
                result["min_price"] = min_price

        except Exception as e:
            self.logger.error(f"Discount validation error: {e}")
            result["valid"] = False
            result["errors"].append(str(e))

        return result

    def apply_discount(self, product_id: int, discount_percent: float, 
                      discount_code: str = None) -> Dict[str, Any]:
        """Apply discount with validation"""
        return self.validate_discount(product_id, discount_percent, discount_code)
