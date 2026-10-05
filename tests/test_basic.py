# -*- coding: utf-8 -*-
"""
Basic tests for Sales.aii infrastructure
"""

import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_database_connection():
    """Test database initialization"""
    from database.database import db
    assert db is not None
    assert db._engine is not None


def test_config_loads():
    """Test configuration loads"""
    from config.config import settings
    assert settings.APP_NAME == "Sales.aii"
    assert settings.APP_VERSION == "1.0.0"


def test_models_exist():
    """Test database models"""
    from database import models
    assert hasattr(models, 'Lead')
    assert hasattr(models, 'Conversation')
    assert hasattr(models, 'Message')


def test_logger_setup():
    """Test logger setup"""
    from utils.logger import logger
    assert logger is not None


def test_agents_import():
    """Test agents can be imported"""
    from agents.lead_agent import LeadAgent
    from agents.sales_agent import SalesAgent
    from agents.support_agent import SupportAgent
    from agents.analytics import Analytics
    
    assert LeadAgent is not None
    assert SalesAgent is not None
    assert SupportAgent is not None
    assert Analytics is not None


def test_integrations_import():
    """Test integrations can be imported"""
    from integrations.reddit import RedditIntegration
    from integrations.github import GitHubIntegration
    from integrations.telegram import TelegramIntegration
    from integrations.shopier import ShopierIntegration
    
    assert RedditIntegration is not None
    assert GitHubIntegration is not None
    assert TelegramIntegration is not None
    assert ShopierIntegration is not None


def test_ai_manager():
    """Test AI manager"""
    from ai.ai_manager import AIManager
    am = AIManager()
    assert am is not None
