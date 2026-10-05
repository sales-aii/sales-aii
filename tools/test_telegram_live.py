# -*- coding: utf-8 -*-
"""
Live Telegram connection test - uses the REAL Bot API.

Not part of the pytest suite on purpose: it sends an actual message to the
owner's chat and needs real credentials in .env.

Usage:  python tools\\test_telegram_live.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.config import settings
from integrations.telegram import TelegramIntegration
from utils.exceptions import APIError


def main() -> int:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("FAIL: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are not set in .env")
        return 2

    telegram = TelegramIntegration()
    print(f"Token: set ({len(token)} chars), chat_id: set")

    try:
        result = telegram.test_connection()
    except APIError as e:
        print(f"FAIL: {e}")
        return 1

    print("OK: Telegram bağlantısı başarılı")
    print(f"  bot        : @{result['bot_username']} (id {result['bot_id']})")
    print(f"  chat_id    : {result['chat_id']}")
    print(f"  message_id : {result['message_id']}")
    print(f"  text       : {result['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())