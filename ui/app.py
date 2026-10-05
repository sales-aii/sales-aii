# -*- coding: utf-8 -*-
"""
Main UI Application
"""

import customtkinter as ctk
from ui.styles import COLORS, apply_theme
from ui.sidebar import Sidebar
from ui.pages.dashboard import DashboardPage
from ui.pages.leads import LeadsPage
from ui.pages.conversations import ConversationsPage
from ui.pages.products import ProductsPage
from ui.pages.sales import SalesPage
from ui.pages.settings import SettingsPage
from utils.logger import logger


class SalesAiiApp(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Apply theme
        apply_theme()
        
        # Window setup
        self.title("Sales.aii")
        self.geometry("1400x900")
        self.minsize(1000, 700)
        self.configure(fg_color=COLORS["bg_primary"])
        
        # Center window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = Sidebar(self, on_nav_change=self.navigate)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Main container
        self.main_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_primary"])
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Pages
        self.pages = {}
        self.current_page = None
        self._init_pages()
        
        # Show dashboard
        self.navigate("Dashboard")
        
        logger.info("UI initialized")
    
    def _init_pages(self):
        """Initialize all pages"""
        self.pages["Dashboard"] = DashboardPage(self.main_frame)
        self.pages["Leads"] = LeadsPage(self.main_frame)
        self.pages["Conversations"] = ConversationsPage(self.main_frame)
        self.pages["Products"] = ProductsPage(self.main_frame)
        self.pages["Sales"] = SalesPage(self.main_frame)
        self.pages["Settings"] = SettingsPage(self.main_frame)
        
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
            page.grid_remove()
    
    def navigate(self, page_name: str):
        """Navigate to page"""
        if self.current_page:
            self.pages[self.current_page].grid_remove()
        
        self.current_page = page_name
        self.pages[page_name].grid()
        
        logger.info(f"Navigated to {page_name}")
    
    def run(self):
        """Run the app"""
        logger.info("Starting Sales.aii UI")
        self.mainloop()


def run_ui():
    """Run UI in main thread"""
    app = SalesAiiApp()
    app.run()
