# -*- coding: utf-8 -*-
"""
Sales page
"""

import customtkinter as ctk
from ui.styles import COLORS, FONTS
from ui.components import Card, EmptyState


class SalesPage(ctk.CTkFrame):
    """Sales page"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_primary"], **kwargs)
        
        header = ctk.CTkFrame(self, fg_color="transparent", height=80)
        header.pack(fill="x", padx=24, pady=(20, 0))
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header,
            text="Sales",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        title.pack(side="left")
        
        table_card = Card(self)
        table_card.pack(fill="both", expand=True, padx=24, pady=24)
        
        cols_frame = ctk.CTkFrame(table_card, fg_color="transparent", height=40)
        cols_frame.pack(fill="x", padx=16, pady=(16, 8))
        cols_frame.pack_propagate(False)
        
        columns = [
            ("Customer", 1),
            ("Product", 2),
            ("Original Price", 1),
            ("Discount", 1),
            ("Final Price", 1),
            ("Payment Status", 1),
            ("Date", 2),
        ]
        
        for i, (col_name, weight) in enumerate(columns):
            col = ctk.CTkLabel(
                cols_frame,
                text=col_name,
                font=FONTS["small"],
                text_color=COLORS["text_secondary"],
                anchor="w"
            )
            col.grid(row=0, column=i, sticky="ew", padx=4)
            cols_frame.grid_columnconfigure(i, weight=weight)
        
        sep = ctk.CTkFrame(table_card, height=1, fg_color=COLORS["border"])
        sep.pack(fill="x", padx=16)
        
        EmptyState(table_card, "No Sales", "No sales recorded yet.").pack(expand=True, fill="both")
