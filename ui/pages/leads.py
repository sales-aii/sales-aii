# -*- coding: utf-8 -*-
"""
Leads page
"""

import customtkinter as ctk
from ui.styles import COLORS, FONTS
from ui.components import Card, EmptyState


class LeadsPage(ctk.CTkFrame):
    """Leads page"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_primary"], **kwargs)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=80)
        header.pack(fill="x", padx=24, pady=(20, 0))
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header,
            text="Leads",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        title.pack(side="left")
        
        # Leads table/card
        table_card = Card(self)
        table_card.pack(fill="both", expand=True, padx=24, pady=24)
        
        # Columns header
        cols_frame = ctk.CTkFrame(table_card, fg_color="transparent", height=40)
        cols_frame.pack(fill="x", padx=16, pady=(16, 8))
        cols_frame.pack_propagate(False)
        
        columns = [
            ("Platform", 1),
            ("Username", 1),
            ("Need", 2),
            ("Product", 1),
            ("Lead Quality", 1),
            ("Status", 1),
            ("Date", 1),
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
        
        # Separator
        sep = ctk.CTkFrame(table_card, height=1, fg_color=COLORS["border"])
        sep.pack(fill="x", padx=16)
        
        # Content
        content = EmptyState(
            table_card,
            title="No Leads",
            message="No leads found. Start by discovering leads from platforms."
        )
        content.pack(expand=True, fill="both")
