# -*- coding: utf-8 -*-
"""
UI Styles - Soft-dark theme for Sales.aii
"""

import customtkinter as ctk


# Color palette - Soft dark theme (not pure black)
COLORS = {
    "bg_primary": "#1e1f22",      # Main background - soft dark
    "bg_secondary": "#2b2d31",    # Cards, panels
    "bg_tertiary": "#36373d",     # Inputs, active states
    "bg_hover": "#404249",        # Hover states
    "accent": "#5865f2",          # Primary accent (blue/purple)
    "accent_hover": "#4752c4",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "danger": "#e74c3c",
    "text_primary": "#f2f3f5",    # Primary text
    "text_secondary": "#b5bac1",  # Secondary text
    "text_muted": "#96989d",     # Muted text
    "border": "#1f2023",          # Borders
}

# Fonts
FONTS = {
    "heading": ("Segoe UI", 20, "bold"),
    "subheading": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 10),
    "body_large": ("Segoe UI", 11),
    "small": ("Segoe UI", 9),
    "button": ("Segoe UI", 10, "bold"),
}


def apply_theme():
    """Apply customtkinter theme"""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Configure root
    ctk.ThemeManager._currently_loaded_theme = "dark-blue"
