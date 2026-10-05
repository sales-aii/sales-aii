# -*- coding: utf-8 -*-
"""
Negotiation engine tests
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_negotiation_levels():
    """Test negotiation levels"""
    from services.negotiation_engine import NegotiationEngine
    ne = NegotiationEngine()
    # Basic logic
    d = ne.determine_discount('interested', True)
    assert d >= 0


def test_weak_signal_restriction():
    """Weak signal shouldn't directly give 40 or 60"""
    from services.negotiation_engine import NegotiationEngine
    ne = NegotiationEngine()
    d = ne.determine_discount('Pahalı', True)
    assert d < 40  # Weak signal, don't give high discount directly


def test_strong_signal():
    """Strong signal handling"""
    from services.negotiation_engine import NegotiationEngine
    ne = NegotiationEngine()
    d = ne.determine_discount('Almak istiyorum ama fiyat yüksek', True, lead_quality='high')
    assert d >= 10


def test_negotiation_step():
    """Test negotiation step with validation"""
    from services.negotiation_engine import NegotiationEngine
    from services.product_service import ProductService
    ne = NegotiationEngine()
    ps = ProductService()
    prod = ps.create_product(name="NegTest", normal_price=100, minimum_price=40)
    if prod is None:
        prods = ps.get_all_products()
        prod = next((p for p in prods if p["name"] == "NegTest"), None)
    if prod:
        res = ne.negotiate_step(prod['id'], 999, 'interested', True, proposed_discount=20)
        assert 'success' in res
        ps.delete_product(prod['id'])


def test_60_is_final():
    """60% is final"""
    from services.negotiation_engine import NegotiationEngine
    from services.product_service import ProductService
    ne = NegotiationEngine()
    ps = ProductService()
    prod = ps.create_product(name="NegTest2", normal_price=100, minimum_price=40)
    if prod is None:
        prods = ps.get_all_products()
        prod = next((p for p in prods if p["name"] == "NegTest2"), None)
    if prod:
        res = ne.negotiate_step(prod['id'], 998, 'strong', True, proposed_discount=60)
        assert res['success'] is True
        assert res.get('is_final_offer') is True
        ps.delete_product(prod['id'])
