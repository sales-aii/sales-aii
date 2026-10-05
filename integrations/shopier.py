# -*- coding: utf-8 -*-
"""
Shopier integration - official Shopier REST API.

Docs:  https://developer.shopier.com/reference/introduction
Base:  https://api.shopier.com/v1/
Auth:  Authorization: Bearer <Personal Access Token | OAuth2 access token>
      Accept: application/json

Order model (https://developer.shopier.com/reference/the-order-model):
    paymentStatus: "paid" | "unpaid"
    status:        "fulfilled" | "unfulfilled"
    refunds[].status: "pending" | "failed" | "succeeded"

A sale is NEVER marked paid without a confirmed "paid" paymentStatus.
"""

from typing import Any, Dict, List, Optional

from config.config import settings
from services.base_service import BaseService
from utils.exceptions import APIError
from utils.http_client import request_json

# Internal sale statuses
STATUS_PAID = "paid"
STATUS_PENDING = "pending"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"


class ShopierIntegration(BaseService):
    """
    Shopier API integration
    Only supported features per official docs are used
    """

    BASE_URL = "https://api.shopier.com/v1"

    def __init__(self):
        super().__init__()
        self.platform = "shopier"
        # SHOPIER_API_TOKEN is the documented auth. Legacy aliases are honoured
        # so older .env files keep working; the secret is only used as a
        # fallback token, never combined with the key.
        self.token = (
            settings.SHOPIER_API_TOKEN
            or settings.SHOPIER_API_KEY
            or settings.SHOPIER_API_SECRET
        )

    def is_configured(self) -> bool:
        """Check if Shopier is configured"""
        return bool(self.token)

    def _require_token(self) -> str:
        if not self.token:
            raise APIError(
                "Shopier: SHOPIER_API_TOKEN (Personal Access Token) is not set"
            )
        return self.token

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._require_token()}",
        }

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        payload = request_json(
            "GET",
            f"{self.BASE_URL}{path}",
            headers=self._headers(),
            params=params,
            platform=self.platform,
            timeout=settings.HTTP_TIMEOUT,
        )
        return payload.get("data", payload)

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------
    @staticmethod
    def map_payment_status(order: Dict[str, Any]) -> str:
        """
        Map the official Shopier order payload to an internal sale status.

        Unknown values map to "pending" - never to "paid".
        """
        if not isinstance(order, dict):
            return STATUS_PENDING

        # A fully refunded order is cancelled
        refunds = order.get("refunds") or []
        if any(r.get("status") == "succeeded" for r in refunds):
            return STATUS_CANCELLED
        if any(r.get("status") == "failed" for r in refunds):
            return STATUS_FAILED

        payment_status = str(order.get("paymentStatus") or "").lower()
        if payment_status == "paid":
            return STATUS_PAID
        if payment_status == "unpaid":
            return STATUS_PENDING
        return STATUS_PENDING

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get a single order by id (https://developer.shopier.com/reference/get-orders-id)"""
        if not order_id:
            raise APIError("Shopier: order_id is required")
        order = self._get(f"/orders/{order_id}")
        if not isinstance(order, dict) or not order:
            raise APIError(f"Shopier: order '{order_id}' returned no data")
        return order

    def check_payment_status(self, order_reference: str) -> Dict[str, Any]:
        """
        Check payment status for an order id.

        Returns {"reference", "status", "paid", "order"} on success and raises
        APIError when the order cannot be read - a failure is never reported
        as a successful "pending" lookup.
        """
        order = self.get_order(order_reference)
        status = self.map_payment_status(order)
        return {
            "reference": order_reference,
            "status": status,
            "paid": status == STATUS_PAID,
            "order": order,
        }

    def list_orders(self, limit: int = 25) -> List[Dict[str, Any]]:
        """List recent orders (https://developer.shopier.com/reference/get-orders)"""
        payload = self._get("/orders", params={"limit": max(1, min(int(limit), 100))})
        if isinstance(payload, dict):
            return payload.get("items") or payload.get("orders") or []
        if isinstance(payload, list):
            return payload
        return []

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------
    def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get a product (https://developer.shopier.com/reference/get-products-id)"""
        if not product_id:
            raise APIError("Shopier: product_id is required")
        product = self._get(f"/products/{product_id}")
        if not isinstance(product, dict) or not product:
            raise APIError(f"Shopier: product '{product_id}' returned no data")
        return product

    def list_products(self, limit: int = 25) -> List[Dict[str, Any]]:
        """List products (https://developer.shopier.com/reference/get-products)"""
        payload = self._get("/products", params={"limit": max(1, min(int(limit), 100))})
        if isinstance(payload, dict):
            return payload.get("items") or payload.get("products") or []
        if isinstance(payload, list):
            return payload
        return []

    def get_product_info(self, product_id: str = None) -> Dict[str, Any]:
        """Product info by id, or an empty dict when no id is given"""
        if not product_id:
            raise APIError("Shopier: product_id is required to fetch product info")
        return self.get_product(product_id)

    # ------------------------------------------------------------------
    # Webhook verification
    # ------------------------------------------------------------------
    def verify_payment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a payment report by re-reading the order from the API.

        A payload is only accepted when the order exists AND Shopier reports
        paymentStatus == "paid". Never trust the incoming body alone.
        """
        if not isinstance(data, dict) or not data:
            raise APIError("Shopier: empty payment payload")

        order_id = data.get("orderId") or data.get("order_id") or data.get("id")
        if not order_id:
            raise APIError("Shopier: payment payload does not contain an order id")

        status = self.check_payment_status(str(order_id))
        verified = status["status"] == STATUS_PAID
        if not verified:
            self.logger.warning(
                f"Shopier: payment for order {order_id} not confirmed "
                f"(status={status['status']})"
            )
        return {
            "verified": verified,
            "status": status["status"],
            "reference": order_id,
            "order": status["order"],
        }