# -*- coding: utf-8 -*-
"""
Sidebar navigation component
"""

import customtkinter as ctk
from ui.styles import COLORS, FONTS


class SidebarButton(ctk.CTkButton):
    """Sidebar navigation button"""
    
    def __init__(self, master, text: str, icon: str = "", command=None, **kwargs):
        super().__init__(
            master,
            text=text,
            font=FONTS["body_large"],
            height=40,
            corner_radius=6,
            fg_color="transparent",
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_secondary"],
            anchor="w",
            command=command,
            **kwargs
        )
        self.is_active = False
    
    def set_active(self, active: bool):
        """Set button active state"""
        self.is_active = active
        if active:
            self.configure(
                fg_color=COLORS["accent"],
                text_color=COLORS["text_primary"],
                hover_color=COLORS["accent_hover"]
            )
        else:
            self.configure(
                fg_color="transparent",
                text_color=COLORS["text_secondary"],
                hover_color=COLORS["bg_hover"]
            )


class Sidebar(ctk.CTkFrame):
    """Main sidebar"""
    
    def __init__(self, master, on_nav_change=None, **kwargs):
        super().__init__(
            master,
            width=240,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=0,
            **kwargs
        )
        self.grid_propagate(False)
        self.on_nav_change = on_nav_change
        self.current_page = "Dashboard"
        
        # Logo/Title
        self.title_label = ctk.CTkLabel(
            self,
            text="Sales.aii",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"]
        )
        self.title_label.pack(pady=(30, 40), padx=20, anchor="w")
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            "Dashboard",
            "Leads",
            "Conversations",
            "Products",
            "Sales",
            "Settings"
        ]
        
        for item in nav_items:
            btn = SidebarButton(
                self,
                text=item,
                command=lambda page=item: self.navigate(page)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[item] = btn
        
        # Set default active
        self.nav_buttons["Dashboard"].set_active(True)
        
        # Spacer
        self.spacer = ctk.CTkFrame(self, fg_color="transparent")
        self.spacer.pack(expand=True, fill="both")
        
        # Footer
        self.version_label = ctk.CTkLabel(
            self,
            text="v1.0.0",
            font=FONTS["small"],
            text_color=COLORS["text_muted"]
        )
        self.version_label.pack(pady=(0, 16), padx=20)
    
    def navigate(self, page: str):
        """Navigate to page"""
        if page == self.current_page:
            return
        
        # Update buttons
        self.nav_buttons[self.current_page].set_active(False)
        self.nav_buttons[page].set_active(True)
        self.current_page = page
        
        if self.on_nav_change:
            self.on_nav_change(page)
    
    def get_current_page(self) -> str:
        return self.current_page
