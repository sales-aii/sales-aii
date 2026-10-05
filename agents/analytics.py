# -*- coding: utf-8 -*-
"""
Analytics module - Normal code + AI when needed
"""

from datetime import datetime
from sqlalchemy import func
from services.base_service import BaseService
from database import models
from utils.exceptions import DatabaseError


class Analytics(BaseService):
    """
    Analytics module for sales insights

    Failures are raised, never reported as "0 leads" - a broken query and a
    genuinely empty database must not look the same to the user.
    """

    def __init__(self):
        super().__init__()
        self.agent_type = "analytics"

    def get_metrics(self):
        """Get key metrics using real DB data"""
        try:
            today = datetime.utcnow().date()
            with self.db.session_scope() as session:
                total_leads = session.query(func.count(models.Lead.id)).scalar() or 0
                leads_today = session.query(func.count(models.Lead.id)).filter(
                    func.date(models.Lead.created_at) == today
                ).scalar() or 0
                replies = session.query(func.count(models.Message.id)).filter(
                    models.Message.sender == 'user'
                ).scalar() or 0
                offers = session.query(func.count(models.Offer.id)).scalar() or 0
                sales = session.query(func.count(models.Sale.id)).scalar() or 0
                revenue = session.query(func.sum(models.Sale.final_price)).scalar() or 0
                avg_discount = session.query(func.avg(models.Sale.discount_percent)).scalar() or 0
                conversion = (sales / total_leads * 100) if total_leads > 0 else 0
                return {
                    'total_leads': total_leads,
                    'leads_today': leads_today,
                    'replies': replies,
                    'offers': offers,
                    'sales': sales,
                    'revenue': float(revenue) if revenue else 0.0,
                    'conversion_rate': round(conversion, 2),
                    'average_discount': round(float(avg_discount), 2) if avg_discount else 0.0
                }
        except Exception as e:
            self.logger.error(f"Metrics error: {e}")
            raise DatabaseError(f"Could not read dashboard metrics: {e}") from e

    def get_recent_activity(self, limit: int = 10):
        """Get recent activity"""
        try:
            with self.db.session_scope() as session:
                logs = session.query(models.ActivityLog).order_by(
                    models.ActivityLog.created_at.desc()
                ).limit(limit).all()
                return [{
                    'action': l.action,
                    'details': l.details,
                    'status': l.status,
                    'created_at': l.created_at
                } for l in logs]
        except Exception as e:
            self.logger.error(f"Activity error: {e}")
            raise DatabaseError(f"Could not read recent activity: {e}") from e

    def generate_insights(self):
        """
        AI-assisted insights.

        Raises APIError when the AI call fails instead of pretending there was
        simply not enough data.
        """
        from ai.ai_manager import AIManager
        ai = AIManager()
        metrics = self.get_metrics()
        # Get product interest
        with self.db.session_scope() as session:
            prod_counts = session.query(models.Product.name, func.count(models.Lead.id)).outerjoin(
                models.Lead, models.Lead.suggested_product_id == models.Product.id
            ).group_by(models.Product.id).all()
        prompt = f"""Give brief insights based on metrics. Return ONLY JSON.
Metrics: {metrics}
Product interest: {prod_counts}
Keys: top_product, best_platform, dropout_stage, summary"""
        return ai.generate_structured_response(prompt)
