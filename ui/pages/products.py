# -*- coding: utf-8 -*-
"""
Products page
"""

import customtkinter as ctk
from ui.styles import COLORS, FONTS
from ui.components import Card, EmptyState


class ProductsPage(ctk.CTkFrame):
    """Products page"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_primary"], **kwargs)
        
        header = ctk.CTkFrame(self, fg_color="transparent", height=80)
        header.pack(fill="x", padx=24, pady=(20, 0))
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header,
            text="Products",
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
            ("Product Name", 1),
            ("Description", 2),
            ("Normal Price", 1),
            ("Minimum Price", 1),
            ("Shopier URL", 2),
            ("Discount Codes", 1),
            ("Active", 1),
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
        
        EmptyState(table_card, "No Products", "No products configured yet.").pack(expand=True, fill="both")
