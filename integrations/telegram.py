# -*- coding: utf-8 -*-
"""
Telegram integration - OWNER NOTIFICATIONS ONLY.

Never used as a customer sales channel.

Official docs: https://core.telegram.org/bots/api#sendmessage
Endpoint:     POST https://api.telegram.org/bot<token>/sendMessage
Response:     {"ok": true, "result": {...}} on success,
              {"ok": false, "error_code": <int>, "description": "<reason>"} on failure
"""

from typing import Any, Dict, Optional

from config.config import settings
from services.base_service import BaseService
from utils.exceptions import APIError
from utils.http_client import request_json


def describe_token_format() -> str:
    """
    The token shape documented by Telegram, for error messages.

    Doc: https://core.telegram.org/bots/api#authorizing-your-bot
    "The token looks something like 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    """
    return "expected <bot_id>:<secret>, e.g. 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


def looks_like_bot_token(value: str) -> bool:
    """
    Cheap shape check for a bot token.

    A real token always carries the "<bot_id>:" prefix. A value without a colon
    is not a token at all - most often a secret that was copied without its
    prefix, which Telegram answers with a bare 404 and no explanation.
    """
    if not value:
        return False
    bot_id, separator, secret = value.partition(":")
    return bool(separator and bot_id.isdigit() and secret)


class TelegramIntegration(BaseService):
    """
    Telegram Bot API integration - used ONLY for owner notifications
    Do not use as customer sales channel
    """

    BASE_URL = "https://api.telegram.org"

    #: HTTP status -> what the user should do about it.
    #: Telegram answers failures with 4xx and its own `description`, so these
    #: hints are what turn "HTTP 403" into something actionable.
    ERROR_HINTS = {
        400: "Bot token or chat_id is not valid.",
        401: "Bot token is not authorized - check TELEGRAM_BOT_TOKEN.",
        403: "The bot cannot write to this chat. Send /start to the bot "
             "first, or check it is still a member of the group.",
        404: "Bot token or chat_id not found - check both values.",
        429: "Rate limited by Telegram - wait before retrying.",
    }

    def __init__(self, bot_token: Optional[str] = None,
                 chat_id: Optional[str] = None):
        """
        Reads the token/chat from .env by default.

        The overrides exist so the Settings connection test can try a value the
        user just typed without editing .env and restarting. Empty overrides
        fall back to .env.
        """
        super().__init__()
        self.platform = "telegram"
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or settings.TELEGRAM_CHAT_ID

    def is_configured(self) -> bool:
        """Check if Telegram is configured"""
        return bool(self.bot_token and self.chat_id)

    def _require_config(self, chat_id: Optional[str]) -> str:
        target = chat_id or self.chat_id
        if not self.bot_token:
            raise APIError("Telegram: TELEGRAM_BOT_TOKEN is not set")
        if not target:
            raise APIError("Telegram: TELEGRAM_CHAT_ID is not set")
        if not looks_like_bot_token(self.bot_token):
            # Caught locally so the user gets the reason instead of a bare 404
            raise APIError(
                f"Telegram: TELEGRAM_BOT_TOKEN is not shaped like a bot "
                f"token ({describe_token_format()}). BotFather gives the full "
                f"token; copy the whole value."
            )
        return str(target)

    def get_me(self) -> Dict[str, Any]:
        """Verify the bot token and return the bot identity"""
        self._require_config(None)
        payload = request_json(
            "GET",
            f"{self.BASE_URL}/bot{self.bot_token}/getMe",
            platform=self.platform,
            timeout=settings.HTTP_TIMEOUT,
            error_hints=self.ERROR_HINTS,
        )
        if not payload.get("ok"):
            raise APIError(self._describe_failure(payload, "getMe"))
        return payload.get("result", {})

    def send_message(self, text: str, chat_id: Optional[str] = None) -> bool:
        """
        Send a message to the owner.

        Returns True only when Telegram itself confirms ok:true.
        Any failure raises APIError - it is never reported as success.
        """
        if not text or not text.strip():
            raise APIError("Telegram: refusing to send an empty message")

        target = self._require_config(chat_id)
        message_id = self._send_and_get_id(text, target)
        return message_id is not None

    def _send_and_get_id(self, text: str, target: str) -> Optional[int]:
        """sendMessage returning Telegram's own message_id"""
        if not text or not text.strip():
            raise APIError("Telegram: refusing to send an empty message")

        url = f"{self.BASE_URL}/bot{self.bot_token}/sendMessage"
        payload = request_json(
            "POST",
            url,
            json={"chat_id": target, "text": text},
            platform=self.platform,
            timeout=settings.HTTP_TIMEOUT,
            error_hints=self.ERROR_HINTS,
        )
        if not payload.get("ok"):
            raise APIError(self._describe_failure(payload, "sendMessage"))

        result = payload.get("result") or {}
        self.logger.info(
            f"Telegram notification delivered to owner "
            f"(message_id={result.get('message_id')})"
        )
        return result.get("message_id")

    def test_notification(self) -> bool:
        """Send a test notification to the owner"""
        return self.send_message("Sales.aii: Test notification")

    def test_connection(self) -> Dict[str, Any]:
        """
        Verify the bot token and the chat, then deliver a real test message.

        Two separate checks so the user learns *which* half is wrong:
        getMe validates the bot token, sendMessage validates that the chat
        exists and that the bot can write to it.

        Raises APIError carrying Telegram's own description on any failure.
        """
        target = self._require_config(None)

        # 1. token check
        bot = self.get_me()
        username = bot.get("username") or bot.get("first_name") or "unknown"

        # 2. real delivery check
        sent_text = "Sales.aii: Telegram bağlantı testi başarılı."
        message_id = self._send_and_get_id(sent_text, target)
        if message_id is None:
            raise APIError(
                "Telegram: sendMessage returned ok:true but no message_id - "
                "cannot confirm the message was delivered."
            )

        self.logger.info(
            f"Telegram connection test succeeded "
            f"(bot=@{username}, chat_id={target}, message_id={message_id})"
        )
        return {
            "bot_username": username,
            "bot_id": bot.get("id"),
            "chat_id": target,
            "message_id": message_id,
            "text": sent_text,
        }

    def _describe_failure(self, payload: Dict[str, Any], call: str) -> str:
        """
        Turn a Telegram error body into a message the user can act on.

        Telegram reports failures as {"ok": false, "error_code": N,
        "description": "..."}; the description is the part worth showing.
        """
        code = payload.get("error_code")
        description = payload.get("description") or "unknown description"
        message = f"Telegram: {call} failed - {description}"
        hint = self.ERROR_HINTS.get(code)
        return f"{message} ({hint})" if hint else message

    def notify_sale_completed(self, sale_info: Dict) -> bool:
        return self.send_message(f"Sale completed: {sale_info}")

    def notify_final_offer(self, info: Dict) -> bool:
        return self.send_message(f"%60 final offer used: {info}")

    def notify_owner_intervention(self, info: Dict) -> bool:
        return self.send_message(f"Owner intervention required: {info}")

    def notify_critical_error(self, error: str) -> bool:
        return self.send_message(f"Critical error: {error}")

    def notify_system_error(self, error: str) -> bool:
        return self.send_message(f"System error: {error}")

    def try_notify(self, text: str) -> bool:
        """
        Best-effort notification: never raises, returns False on failure.

        Used on paths where a notification must not break the main flow.
        """
        try:
            return self.send_message(text)
        except APIError as e:
            self.logger.error(f"Telegram notification failed: {e}")
            return False