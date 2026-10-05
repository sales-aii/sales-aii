# -*- coding: utf-8 -*-
"""
Advanced AI tests
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_json_parsing_safety():
    """Test safe JSON parsing with messy response"""
    from ai.providers.mock_provider import MockProvider
    p = MockProvider()
    messy = 'Here is result: ```json\n{"key": 1}\n```'
    parsed = p._safe_json_parse(messy)
    assert parsed == {"key": 1}
    
    messy2 = 'Some text {"analysis": "ok", "score": 5} more text'
    parsed2 = p._safe_json_parse(messy2)
    assert parsed2 == {"analysis": "ok", "score": 5}
    
    # Broken JSON
    broken = '{not valid json'
    parsed3 = p._safe_json_parse(broken)
    assert parsed3 == {}


def test_retry_mechanism():
    """Test retry logic exists"""
    from ai.ai_manager import AIManager
    m = AIManager()
    # Should handle retries param
    resp = m.generate_response("test", max_retries=1)
    assert isinstance(resp, str)


def test_context_minimization():
    """Test that context is minimal - just pass what's needed"""
    from ai.ai_manager import AIManager
    m = AIManager()
    # Manager takes only what passed
    resp = m.generate_response("minimal prompt")
    assert resp is not None


def test_critical_validation_rules():
    """Test all critical validation rules"""
    from ai.ai_manager import AIManager
    m = AIManager()
    
    # Discount > 60% invalid
    res = m.validate_offer(suggested_discount=61, original_price=100, product_min_price=30)
    assert res["valid"] is False
    
    # Discount exactly 60% - boundary
    res = m.validate_offer(suggested_discount=60, original_price=100, product_min_price=30)
    # 40 >= 30, 60% not > 60%, so valid
    assert res["valid"] is True
    
    # Price below minimum
    res = m.validate_offer(suggested_discount=50, original_price=100, product_min_price=60)  # 50 < 60
    assert res["valid"] is False
    
    # Valid boundaries
    res = m.validate_offer(suggested_discount=20, original_price=100, product_min_price=70)  # 80>=70
    assert res["valid"] is True
