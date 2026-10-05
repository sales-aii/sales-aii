# -*- coding: utf-8 -*-
"""
Conversations page
"""

import customtkinter as ctk
from ui.styles import COLORS, FONTS
from ui.components import Card, EmptyState


class ConversationsPage(ctk.CTkFrame):
    """Conversations page - Left list, Right details"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_primary"], **kwargs)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.pack(fill="x", padx=24, pady=(20, 0))
        header.pack_propagate(False)
        
        title = ctk.CTkLabel(
            header,
            text="Conversations",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        title.pack(side="left")
        
        # Main content - split view
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        content.grid_columnconfigure((0, 1), weight=1, uniform="convo")
        content.grid_rowconfigure(0, weight=1)
        
        # Left panel - Conversations list
        left_panel = Card(content)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        
        left_header = ctk.CTkLabel(
            left_panel,
            text="Conversations",
            font=FONTS["subheading"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        left_header.pack(pady=(16, 12), padx=16, anchor="w")
        
        EmptyState(left_panel, "No Conversations", "No active conversations").pack(expand=True, fill="both")
        
        # Right panel - Conversation details
        right_panel = Card(content)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        
        right_header = ctk.CTkLabel(
            right_panel,
            text="Conversation Details",
            font=FONTS["subheading"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        right_header.pack(pady=(16, 12), padx=16, anchor="w")
        
        # Info section
        info_frame = ctk.CTkFrame(right_panel, fg_color=COLORS["bg_tertiary"], corner_radius=6)
        info_frame.pack(fill="x", padx=16, pady=(0, 12))
        
        info_text = """Platform: -
Username: -
Lead: -
Need: -"""
        
        info_label = ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="w",
            justify="left"
        )
        info_label.pack(pady=12, padx=12, anchor="w")
        
        # History
        history_label = ctk.CTkLabel(
            right_panel,
            text="Conversation History",
            font=FONTS["body_large"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        history_label.pack(pady=(0, 8), padx=16, anchor="w")
        
        history_frame = ctk.CTkFrame(right_panel, fg_color=COLORS["bg_tertiary"], corner_radius=6)
        history_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        
        EmptyState(history_frame, "No History", "Select a conversation").pack(expand=True, fill="both")
        
        # AI Analysis
        analysis_label = ctk.CTkLabel(
            right_panel,
            text="AI Analysis",
            font=FONTS["body_large"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        analysis_label.pack(pady=(0, 8), padx=16, anchor="w")
        
        analysis_frame = ctk.CTkFrame(right_panel, fg_color=COLORS["bg_tertiary"], corner_radius=6, height=80)
        analysis_frame.pack(fill="x", padx=16, pady=(0, 12))
        analysis_frame.pack_propagate(False)
        
        EmptyState(analysis_frame, "No Analysis", "").pack(expand=True, fill="both")
        
        # Draft response
        draft_label = ctk.CTkLabel(
            right_panel,
            text="Draft Response",
            font=FONTS["body_large"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        draft_label.pack(pady=(0, 8), padx=16, anchor="w")
        
        draft_text = ctk.CTkTextbox(
            right_panel,
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            font=FONTS["body"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=6,
            height=100
        )
        draft_text.pack(fill="x", padx=16, pady=(0, 12))
        draft_text.insert("1.0", "Draft response will appear here...")
        
        # Buttons
        btn_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))
        
        btns = [
            ("Düzenle", COLORS["bg_hover"]),
            ("Reddet", COLORS["warning"]),
            ("Gönder", COLORS["accent"]),
        ]
        
        for text, color in btns:
            btn = ctk.CTkButton(
                btn_frame,
                text=text,
                font=FONTS["button"],
                fg_color=color,
                hover_color=color,
                text_color=COLORS["text_primary"],
                height=36,
                corner_radius=6
            )
            btn.pack(side="right", padx=4)
