# -*- coding: utf-8 -*-
"""
Dashboard page
"""

import customtkinter as ctk
from datetime import datetime
from ui.styles import COLORS, FONTS
from ui.components import Card, MetricCard, EmptyState, ErrorState
from ui.tasks import run_bg
from utils.logger import logger
from agents.analytics import Analytics


class DashboardPage(ctk.CTkFrame):
    """Dashboard page"""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_primary"], **kwargs)
        self.analytics = Analytics()

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=80)
        header.pack(fill="x", padx=24, pady=(20, 0))
        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="Dashboard",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        title.pack(side="left")

        # Time
        self.time_label = ctk.CTkLabel(
            header,
            text=datetime.now().strftime("%Y-%m-%d %H:%M"),
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            anchor="e"
        )
        self.time_label.pack(side="right")

        # Metrics grid
        metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=24, pady=24)
        metrics_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metrics")
        metrics_frame.grid_rowconfigure((0, 1), weight=1)

        # Metric cards
        self.leads_today = MetricCard(metrics_frame, title="Leads Today", value="0", subtitle="New leads")
        self.leads_today.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 12))

        self.replies = MetricCard(metrics_frame, title="Replies", value="0", subtitle="Responses")
        self.replies.grid(row=0, column=1, sticky="nsew", padx=6, pady=(0, 12))

        self.offers = MetricCard(metrics_frame, title="Offers", value="0", subtitle="Active offers")
        self.offers.grid(row=0, column=2, sticky="nsew", padx=6, pady=(0, 12))

        self.sales = MetricCard(metrics_frame, title="Sales", value="0", subtitle="Closed deals")
        self.sales.grid(row=0, column=3, sticky="nsew", padx=(12, 0), pady=(0, 12))

        self.revenue = MetricCard(metrics_frame, title="Revenue", value="0", subtitle="Total revenue")
        self.revenue.grid(row=1, column=0, sticky="nsew", padx=(0, 12), pady=(0, 12))

        self.conversion = MetricCard(metrics_frame, title="Conversion Rate", value="0%", subtitle="Success rate")
        self.conversion.grid(row=1, column=1, sticky="nsew", padx=6, pady=(0, 12))

        self.avg_discount = MetricCard(metrics_frame, title="Average Discount", value="0%", subtitle="Avg discount")
        self.avg_discount.grid(row=1, column=2, sticky="nsew", padx=6, pady=(0, 12))

        self.total_leads = MetricCard(metrics_frame, title="Total Leads", value="0", subtitle="All leads")
        self.total_leads.grid(row=1, column=3, sticky="nsew", padx=(12, 0), pady=(0, 12))

        # Recent Activity
        activity_card = Card(self)
        activity_card.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        activity_header = ctk.CTkLabel(activity_card, text="Recent Activity", font=FONTS["subheading"], text_color=COLORS["text_primary"], anchor="w")
        activity_header.pack(pady=(16, 12), padx=16, anchor="w")

        self.activity_content = EmptyState(activity_card, title="No Activity", message="No recent activity to display")
        self.activity_content.pack(expand=True, fill="both")

        self.load_dashboard_data()

    def load_dashboard_data(self):
        """
        Load dashboard data without blocking the UI.

        The DB query runs on a worker thread; a failure is shown to the user
        instead of leaving stale zeros on screen.
        """
        run_bg(
            self,
            self.analytics.get_metrics,
            on_success=self._apply_metrics,
            on_error=self._show_error,
        )

    def _apply_metrics(self, m):
        self.leads_today.update_value(str(m['leads_today']))
        self.replies.update_value(str(m['replies']))
        self.offers.update_value(str(m['offers']))
        self.sales.update_value(str(m['sales']))
        self.revenue.update_value(f"{m['revenue']:.2f}")
        self.conversion.update_value(f"{m['conversion_rate']}%")
        self.avg_discount.update_value(f"{m['average_discount']}%")
        self.total_leads.update_value(str(m['total_leads']))

    def _show_error(self, error):
        logger.error(f"Error loading dashboard data: {error}")
        for card in (self.leads_today, self.replies, self.offers, self.sales,
                     self.revenue, self.conversion, self.avg_discount,
                     self.total_leads):
            card.update_value("-")
        for child in self.winfo_children():
            if isinstance(child, ErrorState):
                return
        error_state = ErrorState(
            self,
            title="Could not load metrics",
            message=str(error),
        )
        error_state.pack(fill="x", padx=24, pady=(0, 12))
