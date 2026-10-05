# -*- coding: utf-8 -*-
"""
Settings page with categories.

Shows real configuration state (which provider is live, which integrations are
usable) so the user is never misled into thinking an API is connected when it
is not. Secrets are only ever reported as present/absent.
"""

import customtkinter as ctk
from ui.styles import COLORS, FONTS
from ui.components import Card
from ui.tasks import run_bg
from config.config import settings
from integrations.telegram import TelegramIntegration


def _mask(value) -> str:
    """Report a secret as present without revealing it."""
    if not value:
        return "not set"
    return f"set ({len(str(value))} chars)"


class TelegramConnectionPanel(ctk.CTkFrame):
    """
    Bot Token / Chat ID entries plus a real connection test.

    The test is a genuine Telegram Bot API call: getMe validates the token,
    sendMessage proves the bot can actually deliver to the chat. A failure is
    reported with Telegram's own error text - never as a success.
    """

    def __init__(self, master, draft: dict = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        values = draft or {
            "bot_token": settings.TELEGRAM_BOT_TOKEN,
            "chat_id": settings.TELEGRAM_CHAT_ID,
        }

        # -- fields ---------------------------------------------------
        fields = ctk.CTkFrame(self, fg_color="transparent")
        fields.pack(fill="x", pady=(4, 0))

        self.token_entry = self._labelled_field(
            fields, "Bot Token", values["bot_token"], show="*"
        )
        self.chat_entry = self._labelled_field(
            fields, "Chat ID", values["chat_id"]
        )

        # -- test button ----------------------------------------------
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", pady=(16, 0))

        self.test_button = ctk.CTkButton(
            actions,
            text="Test Bildirimi",
            font=FONTS["button"],
            height=36,
            corner_radius=6,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            width=160,
            command=self.start_test,
        )
        self.test_button.pack(side="left")

        self.status_label = ctk.CTkLabel(
            actions,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
            anchor="w",
            justify="left",
            wraplength=380,
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=(12, 0))

        self._set_status(
            "Values come from .env. Edit them here to test a correction "
            "without touching the file."
        )

    @staticmethod
    def _labelled_field(parent, label: str, value: str, show: str = ""):
        """A label + entry pair, returning the entry"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)

        ctk.CTkLabel(
            row,
            text=label,
            font=FONTS["body"],
            text_color=COLORS["text_secondary"],
            anchor="w",
            width=180,
        ).pack(side="left")

        entry = ctk.CTkEntry(
            row,
            height=30,
            corner_radius=6,
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            font=FONTS["body"],
        )
        if value:
            entry.insert(0, value)
        if show:
            entry.configure(show=show)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def values(self) -> tuple:
        """Current field values, whitespace trimmed"""
        return (
            (self.token_entry.get() or "").strip(),
            (self.chat_entry.get() or "").strip(),
        )

    # -- test flow -----------------------------------------------------
    def start_test(self):
        """Run the connection test off the Tk thread"""
        bot_token, chat_id = self.values()
        if not bot_token:
            self._set_status(
                "TELEGRAM_BOT_TOKEN is empty - set it in .env or above.",
                COLORS["danger"],
            )
            return
        if not chat_id:
            self._set_status(
                "TELEGRAM_CHAT_ID is empty - set it in .env or above.",
                COLORS["danger"],
            )
            return

        self._set_status("Waiting for Telegram...", COLORS["text_secondary"])
        run_bg(
            self,
            lambda: TelegramIntegration(bot_token, chat_id).test_connection(),
            on_success=self._on_success,
            on_error=self._on_error,
            busy_callback=self._set_busy,
        )

    def _set_busy(self, busy: bool):
        self.test_button.configure(
            state="disabled" if busy else "normal",
            text="Testing..." if busy else "Test Bildirimi",
        )

    def _on_success(self, result):
        self._set_status(
            "Telegram bağlantısı başarılı\n"
            f"Bot: @{result['bot_username']} (id {result['bot_id']})  |  "
            f"Chat: {result['chat_id']}  |  "
            f"Message ID: {result['message_id']}",
            COLORS["success"],
        )

    def _on_error(self, error):
        self._set_status(
            f"Telegram bağlantısı başarısız\n{error}",
            COLORS["danger"],
        )

    def _set_status(self, text: str, color: str = None):
        self.status_label.configure(
            text=text,
            text_color=color or COLORS["text_muted"],
        )


class SettingsCategory(ctk.CTkButton):
    """Settings category button"""

    def __init__(self, master, text: str, command=None, **kwargs):
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


class SettingsPage(ctk.CTkFrame):
    """Settings page with category system"""

    #: category -> rows of (label, value)
    def _build_rows(self):
        from ai.ai_manager import AIManager

        ai = AIManager()
        if ai.is_real_provider_active():
            ai_status = f"ACTIVE - real {ai.active_provider} ({ai.get_active_model()})"
        else:
            ai_status = (
                f"OFFLINE - using '{ai.active_provider}' canned responses. "
                "No API call is being made."
            )

        return {
            "General": [
                ("App version", f"{settings.APP_NAME} {settings.APP_VERSION}"),
                ("AI provider setting", settings.AI_PROVIDER),
                ("AI status", ai_status),
                ("AI timeout / retries", f"{settings.AI_TIMEOUT}s / {settings.AI_MAX_RETRIES}"),
                ("Log level", settings.LOG_LEVEL),
                ("Database", str(settings.DB_PATH)),
            ],
            "AI": [
                ("Status", ai_status),
                ("Gemini API key", _mask(settings.GEMINI_API_KEY)),
                ("Gemini model", settings.GEMINI_MODEL),
                ("Timeout (s)", str(settings.AI_TIMEOUT)),
                ("Max retries", str(settings.AI_MAX_RETRIES)),
            ],
            "Reddit": [
                ("Client ID", _mask(settings.REDDIT_CLIENT_ID)),
                ("Client secret", _mask(settings.REDDIT_CLIENT_SECRET)),
                ("User agent", settings.REDDIT_USER_AGENT),
            ],
            "GitHub": [
                ("Token", _mask(settings.GITHUB_TOKEN)),
                ("API version", settings.GITHUB_API_VERSION),
            ],
            "Telegram": [
                ("Bot token", _mask(settings.TELEGRAM_BOT_TOKEN)),
                ("Chat ID", _mask(settings.TELEGRAM_CHAT_ID)),
                ("Purpose", "Owner notifications only - never a sales channel"),
            ],
            "Shopier": [
                ("API token (PAT)", _mask(settings.SHOPIER_API_TOKEN)),
                ("Legacy key", _mask(settings.SHOPIER_API_KEY)),
                ("Purpose", "Payment status verification"),
            ],
        }

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["bg_primary"], **kwargs)
        self.current_category = "General"
        #: last values typed in the Telegram panel, kept across category switches
        self.telegram_draft = {
            "bot_token": settings.TELEGRAM_BOT_TOKEN,
            "chat_id": settings.TELEGRAM_CHAT_ID,
        }
        self.telegram_panel = None

        header = ctk.CTkFrame(self, fg_color="transparent", height=80)
        header.pack(fill="x", padx=24, pady=(20, 0))
        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="Settings",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        title.pack(side="left")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        content.grid_columnconfigure((0, 1), weight=1, uniform="settings")
        content.grid_rowconfigure(0, weight=1)

        # Categories sidebar
        categories_panel = Card(content, width=220)
        categories_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        categories_panel.grid_propagate(False)

        cat_header = ctk.CTkLabel(
            categories_panel,
            text="Categories",
            font=FONTS["subheading"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        cat_header.pack(pady=(16, 12), padx=16, anchor="w")

        self.cat_buttons = {}
        categories = ["AI", "Reddit", "GitHub", "Telegram", "Shopier", "General"]
        for cat in categories:
            btn = SettingsCategory(
                categories_panel,
                text=cat,
                command=lambda c=cat: self.switch_category(c)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.cat_buttons[cat] = btn
        self.cat_buttons["General"].set_active(True)

        # Settings content
        self.settings_panel = Card(content)
        self.settings_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        self.rows = self._build_rows()
        self.show_category("General")

    def switch_category(self, category: str):
        if category == self.current_category:
            return
        self.cat_buttons[self.current_category].set_active(False)
        self.cat_buttons[category].set_active(True)
        self.current_category = category
        self.show_category(category)

    def _stash_telegram_draft(self):
        """Remember what the user typed before the panel is rebuilt"""
        if self.telegram_panel is not None:
            token, chat_id = self.telegram_panel.values()
            self.telegram_draft = {"bot_token": token, "chat_id": chat_id}

    def show_category(self, category: str):
        self._stash_telegram_draft()
        self.telegram_panel = None

        # Clear panel
        for widget in self.settings_panel.winfo_children():
            widget.destroy()

        header = ctk.CTkLabel(
            self.settings_panel,
            text=f"{category} Settings",
            font=FONTS["subheading"],
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        header.pack(pady=(16, 20), padx=20, anchor="w")

        content_frame = ctk.CTkFrame(self.settings_panel, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20)

        for label, value in self.rows.get(category, []):
            row = ctk.CTkFrame(content_frame, fg_color="transparent")
            row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                row,
                text=label,
                font=FONTS["body"],
                text_color=COLORS["text_secondary"],
                anchor="w",
                width=180,
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=str(value),
                font=FONTS["body"],
                text_color=COLORS["text_primary"],
                anchor="w",
                justify="left",
                wraplength=420,
            ).pack(side="left", fill="x", expand=True)

        if category == "Telegram":
            self.telegram_panel = TelegramConnectionPanel(
                content_frame, draft=self.telegram_draft
            )
            self.telegram_panel.pack(fill="x", pady=(12, 0), anchor="nw")

        note = ctk.CTkLabel(
            content_frame,
            text=(
                "API keys are read from the .env file next to the executable "
                "(or in the project folder when running from source).\n"
                "The app starts and runs without any keys - unconfigured "
                "integrations are reported as unavailable instead of "
                "pretending to work."
            ),
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="nw",
            justify="left",
        )
        note.pack(anchor="nw", pady=(16, 0))