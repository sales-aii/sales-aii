# -*- coding: utf-8 -*-
"""
Mock Telegram
"""

class MockTelegramIntegration:
    """
    Telegram stand-in for unit tests.

    Records what it was asked to send instead of claiming delivery, so a test
    can never pass on a message that no real bot ever received.
    """

    def __init__(self):
        self.platform = "telegram"
        self.sent_messages = []

    def is_configured(self) -> bool:
        return True

    def send_message(self, text: str, chat_id: str = None) -> bool:
        self.sent_messages.append({'text': text, 'chat_id': chat_id})
        return True

    def test_notification(self) -> bool:
        return self.send_message("Sales.aii: Test notification")
