# -*- coding: utf-8 -*-
"""
Mock Shopier
"""

from typing import Dict, Any


class MockShopierIntegration:
    def __init__(self):
        self.platform = "shopier"

    def is_configured(self) -> bool:
        return True

    def check_payment_status(self, order_reference: str) -> Dict[str, Any]:
        return {"reference": order_reference, "status": "pending", "paid": False}

    def verify_payment(self, data: Dict) -> Dict[str, Any]:
        return {"verified": False, "status": "pending"}
