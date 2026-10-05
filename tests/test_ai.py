# -*- coding: utf-8 -*-
"""
AI Manager tests with mock provider
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_ai_manager_initialization():
    """Test AI manager initializes"""
    from ai.ai_manager import AIManager
    manager = AIManager()
    assert manager is not None
    assert len(manager.providers) > 0
    assert manager.active_provider is not None


def test_mock_provider():
    """Test mock provider works"""
    from ai.providers.mock_provider import MockProvider
    provider = MockProvider()
    assert provider.is_configured() is True
    resp = provider.generate("test")
    assert resp is not None


def test_generate_response():
    """Test generate response"""
    from ai.ai_manager import AIManager
    manager = AIManager()
    resp = manager.generate_response("hello")
    assert isinstance(resp, str)


def test_generate_structured():
    """Test structured response"""
    from ai.ai_manager import AIManager
    manager = AIManager()
    resp = manager.generate_structured_response("give analysis")
    assert isinstance(resp, dict)


def test_provider_selection():
    """Test provider selection"""
    from ai.ai_manager import AIManager
    manager = AIManager()
    providers = manager.get_available_providers()
    assert isinstance(providers, list)
    assert len(providers) > 0
    manager.set_active_provider(providers[0])
    assert manager.active_provider == providers[0]


def test_validate_offer():
    """Test offer validation - critical rules"""
    from ai.ai_manager import AIManager
    manager = AIManager()
    # Normal case
    res = manager.validate_offer(product_min_price=80, suggested_discount=10, original_price=100)
    assert res["valid"] is True
    
    # Over 60% discount - should be invalid
    res = manager.validate_offer(product_min_price=80, suggested_discount=70, original_price=100)
    assert res["valid"] is False
    
    # Below minimum price - should be invalid
    res = manager.validate_offer(product_min_price=80, suggested_discount=50, original_price=100)  # 50 = 50, below 80? 50<80 true
    assert res["valid"] is False
    
    # Valid case
    res = manager.validate_offer(product_min_price=80, suggested_discount=10, original_price=100)  # 90>80
    assert res["valid"] is True


def test_no_real_api_keys_required():
    """The AI layer works without any real API key"""
    from ai.ai_manager import AIManager
    manager = AIManager()
    assert manager.active_provider == "mock"
    resp = manager.generate_response("test")
    assert resp
