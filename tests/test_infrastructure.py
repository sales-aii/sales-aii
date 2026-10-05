# -*- coding: utf-8 -*-
"""
Infrastructure tests: imports, configuration and startup without API keys.
"""

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CORE_MODULES = [
    "config.config",
    "utils.logger",
    "utils.exceptions",
    "utils.http_client",
    "database.database",
    "database.models",
    "services.base_service",
    "repositories.base_repository",
    "agents.lead_agent",
    "agents.sales_agent",
    "agents.support_agent",
    "agents.analytics",
    "ai.ai_manager",
    "ai.providers.base_provider",
    "ai.providers.mock_provider",
    "ai.providers.gemini_provider",
    "integrations.reddit",
    "integrations.github",
    "integrations.telegram",
    "integrations.shopier",
    "integrations.mock.reddit_mock",
    "integrations.mock.github_mock",
    "integrations.mock.telegram_mock",
    "integrations.mock.shopier_mock",
    "ui.styles",
    "ui.components",
    "ui.tasks",
]


@pytest.mark.parametrize("module_name", CORE_MODULES)
def test_module_imports(module_name):
    """Every core module must import without a network call or a key"""
    module = importlib.import_module(module_name)
    assert module is not None


def test_app_initializes_without_api_keys():
    from config.config import settings
    from database.database import db
    from ai.ai_manager import AIManager

    assert db is not None
    assert settings is not None

    # conftest blanks every key, so the app must fall back to the mock provider
    manager = AIManager()
    assert manager.active_provider == "mock"
    assert manager.is_real_provider_active() is False


def test_every_integration_reports_itself_unconfigured():
    """No integration may claim to be ready without credentials"""
    from integrations.github import GitHubIntegration
    from integrations.reddit import RedditIntegration
    from integrations.shopier import ShopierIntegration
    from integrations.telegram import TelegramIntegration

    for cls in (RedditIntegration, GitHubIntegration, TelegramIntegration,
                ShopierIntegration):
        assert cls().is_configured() is False, \
            f"{cls.__name__} claims to be configured with no keys"


def test_config_paths_are_absolute():
    from config.config import settings

    assert settings.BASE_DIR.is_absolute()
    assert settings.DATA_DIR.is_absolute()
    assert settings.LOGS_DIR.is_absolute()
    assert settings.DB_PATH is not None
    assert settings.DATA_DIR.exists()
    assert settings.LOGS_DIR.exists()