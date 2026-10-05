# -*- coding: utf-8 -*-
"""
UI smoke tests.

The UI modules must at least import and describe their pages without a running
display. This catches missing font keys, renamed methods and syntax errors that
would otherwise only surface when the app is opened.
"""

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ui.styles import COLORS, FONTS  # noqa: E402
from utils.exceptions import APIError  # noqa: E402


class _FakeWidget:
    """Stand-in for a CTk widget: records configure() calls, needs no display"""

    def __init__(self):
        self.config = {}

    def configure(self, **kwargs):
        self.config.update(kwargs)


def test_styles_define_every_referenced_font():
    """Any font key used by a page must exist in FONTS"""
    used = set()
    for path in (PROJECT_ROOT / "ui").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        used.update(
            part.split('"')[1]
            for part in text.split("FONTS[")[1:]
            if '"' in part
        )
    missing = used - set(FONTS)
    assert not missing, f"undefined font keys: {missing}"


def test_sidebar_pages_can_be_imported():
    """Every page module must import cleanly"""
    for name in (
        "dashboard", "leads", "conversations",
        "products", "sales", "settings",
    ):
        module = importlib.import_module(f"ui.pages.{name}")
        assert hasattr(module, "SettingsPage") or module
        assert [n for n in dir(module)
                if n.endswith("Page")], f"no page class in {name}"


def test_settings_page_rows_never_leak_secrets(monkeypatch):
    """
    Settings must report secrets as present/absent, never as their value.
    """
    from config.config import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "SUPER-SECRET-VALUE")
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_SECRETVALUE")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "123:SECRET")

    from ui.pages.settings import SettingsPage, _mask

    assert "SUPER-SECRET-VALUE" not in _mask(settings.GEMINI_API_KEY)
    assert _mask(settings.GEMINI_API_KEY).startswith("set (")
    assert _mask(None) == "not set"

    page = SettingsPage.__new__(SettingsPage)  # no Tk root needed
    rows = SettingsPage._build_rows(page)
    flat = " ".join(str(v) for values in rows.values() for _l, v in values)
    assert "SUPER-SECRET-VALUE" not in flat
    assert "ghp_SECRETVALUE" not in flat
    assert "123:SECRET" not in flat


def test_settings_page_reports_ai_status():
    """The user must be able to see whether a real provider is live"""
    from config.config import settings
    from ui.pages.settings import SettingsPage

    page = SettingsPage.__new__(SettingsPage)
    rows = SettingsPage._build_rows(page)

    status = dict((k, v) for k, v in rows["AI"])["Status"]
    # tests run with AI_PROVIDER=mock, so it must say it is offline
    assert settings.AI_PROVIDER == "mock"
    assert "OFFLINE" in status
    assert "No API call" in status


def test_telegram_panel_validates_fields_before_calling_the_api(monkeypatch):
    """
    An empty token or chat id must be reported without touching the network -
    the UI must never fire a request it already knows will fail.
    """
    import ui.pages.settings as settings_page

    panel = settings_page.TelegramConnectionPanel.__new__(
        settings_page.TelegramConnectionPanel
    )
    panel.test_button = _FakeWidget()
    panel.status_label = _FakeWidget()

    class _Entries:
        @staticmethod
        def get():
            return "   "

    panel.token_entry = _Entries()
    panel.chat_entry = _Entries()

    class _ExplodingIntegration:
        def __init__(self, *args, **kwargs):
            raise AssertionError("no API call may be made with empty fields")

    monkeypatch.setattr(
        settings_page, "TelegramIntegration", _ExplodingIntegration
    )
    monkeypatch.setattr(
        settings_page, "run_bg",
        lambda *a, **k: pytest.fail("run_bg must not be reached"),
    )

    panel.start_test()

    assert "TELEGRAM_BOT_TOKEN" in panel.status_label.config["text"]
    assert panel.status_label.config["text_color"] == COLORS["danger"]
    # the button was never put into its busy state
    assert panel.test_button.config.get("state", "normal") == "normal"


def test_telegram_panel_success_message_is_the_agreed_text():
    """The user asked for a specific confirmation wording"""
    from ui.pages.settings import TelegramConnectionPanel

    panel = TelegramConnectionPanel.__new__(TelegramConnectionPanel)
    panel.status_label = _FakeWidget()

    panel._on_success(
        {
            "bot_username": "sales_aii_bot",
            "bot_id": 7,
            "chat_id": "12345",
            "message_id": 42,
        }
    )

    text = panel.status_label.config["text"]
    assert "Telegram bağlantısı başarılı" in text
    assert panel.status_label.config["text_color"] == COLORS["success"]
    assert "@sales_aii_bot" in text
    assert "42" in text


def test_telegram_panel_shows_the_real_api_error():
    """Failures must surface Telegram's own text, not a generic message"""
    from ui.pages.settings import TelegramConnectionPanel

    panel = TelegramConnectionPanel.__new__(TelegramConnectionPanel)
    panel.status_label = _FakeWidget()

    panel._on_error(APIError("telegram: HTTP 400 for POST api.telegram.org: chat not found"))

    text = panel.status_label.config["text"]
    assert "başarısız" in text
    assert "chat not found" in text
    assert panel.status_label.config["text_color"] == COLORS["danger"]


def test_telegram_panel_button_is_busy_during_the_call():
    """A second click while the request is in flight must be impossible"""
    from ui.pages.settings import TelegramConnectionPanel

    panel = TelegramConnectionPanel.__new__(TelegramConnectionPanel)
    panel.test_button = _FakeWidget()

    panel._set_busy(True)
    assert panel.test_button.config["state"] == "disabled"

    panel._set_busy(False)
    assert panel.test_button.config["state"] == "normal"
    assert panel.test_button.config["text"] == "Test Bildirimi"


def test_every_page_has_referenced_colors():
    """Guard against a renamed color key"""
    for path in (PROJECT_ROOT / "ui").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for part in text.split('COLORS["')[1:]:
            key = part.split('"')[0]
            assert key in COLORS, f"{path.name} uses undefined color '{key}'"