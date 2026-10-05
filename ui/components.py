# -*- coding: utf-8 -*-
"""
Reusable UI components
"""

import customtkinter as ctk
from ui.styles import COLORS, FONTS


class Card(ctk.CTkFrame):
    """Card component"""
    
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=8,
            **kwargs
        )
        self.grid_propagate(False)


class MetricCard(Card):
    """Metric card for dashboard"""
    
    def __init__(self, master, title: str, value: str = "0", subtitle: str = "", **kwargs):
        super().__init__(master, **kwargs)
        
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        self.title_label.pack(pady=(12, 4), padx=16, anchor="w")
        
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=("Segoe UI", 32, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.value_label.pack(padx=16, anchor="w")
        
        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=FONTS["small"],
            text_color=COLORS["text_muted"]
        )
        self.subtitle_label.pack(pady=(4, 12), padx=16, anchor="w")
    
    def update_value(self, value: str):
        """Update metric value"""
        self.value_label.configure(text=value)


class LoadingSpinner(ctk.CTkFrame):
    """Loading state component"""
    
    def __init__(self, master, text: str = "Loading...", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.label = ctk.CTkLabel(
            self,
            text=text,
            font=FONTS["body_large"],
            text_color=COLORS["text_secondary"]
        )
        self.label.pack(pady=20, padx=20)


class EmptyState(ctk.CTkFrame):
    """Empty state component"""
    
    def __init__(self, master, title: str = "No data", message: str = "Nothing to show here", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=FONTS["subheading"],
            text_color=COLORS["text_primary"]
        )
        self.title_label.pack(pady=(20, 8), padx=20)
        
        self.message_label = ctk.CTkLabel(
            self,
            text=message,
            font=FONTS["body"],
            text_color=COLORS["text_muted"]
        )
        self.message_label.pack(pady=(0, 20), padx=20)


class ErrorState(ctk.CTkFrame):
    """Error state component"""
    
    def __init__(self, master, title: str = "Error", message: str = "Something went wrong", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=FONTS["subheading"],
            text_color=COLORS["danger"]
        )
        self.title_label.pack(pady=(20, 8), padx=20)
        
        self.message_label = ctk.CTkLabel(
            self,
            text=message,
            font=FONTS["body"],
            text_color=COLORS["text_muted"]
        )
        self.message_label.pack(pady=(0, 20), padx=20)
