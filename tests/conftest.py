# -*- coding: utf-8 -*-
"""
Pytest configuration.

Tests must never touch the real data/ directory, otherwise fake leads,
products and sales end up in the user's database. Every env var below is set
BEFORE config.config is imported, so the whole suite runs against an isolated
temporary SQLite file.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Isolate storage before anything imports config.config
# ---------------------------------------------------------------------------
_TEST_ROOT = Path(tempfile.mkdtemp(prefix="sales_aii_tests_"))
os.environ["DATA_DIR"] = str(_TEST_ROOT / "data")
os.environ["LOGS_DIR"] = str(_TEST_ROOT / "logs")
os.environ["DB_NAME"] = "test_sales_aii.db"
os.environ["LOG_LEVEL"] = "WARNING"
# Never let a developer's real keys leak into tests or trigger real API calls.
# Env vars take priority over .env in pydantic-settings, so empty values are
# written to shadow any key stored in the developer's .env file.
for _key in (
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "GITHUB_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "SHOPIER_API_TOKEN",
    "SHOPIER_API_KEY",
    "SHOPIER_API_SECRET",
):
    os.environ[_key] = ""
# A stray .env in the project root must not switch tests to a paid provider
os.environ["AI_PROVIDER"] = "mock"


import pytest


@pytest.fixture(autouse=True)
def clean_state():
    """
    Start every test from an empty database and a clean outbound channel list.

    Without this, data created by an earlier test would make later assertions
    look like failures (or, worse, pass for the wrong reason). Rows are deleted
    instead of dropping the schema, which keeps the suite fast.
    """
    from database.database import db
    from database.models import Base
    from services.message_service import MessageService

    with db._engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.exec_driver_sql(f'DELETE FROM "{table.name}"')
    # the sender registry is class level, so it must be reset between tests
    MessageService._senders.clear()
    yield
    MessageService._senders.clear()


def pytest_sessionfinish(session, exitstatus):
    """Close the engine and delete the temporary database directory"""
    try:
        from database.database import db
        db.dispose()
    except Exception:
        pass
    shutil.rmtree(_TEST_ROOT, ignore_errors=True)