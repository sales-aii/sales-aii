# -*- coding: utf-8 -*-
"""
Sales agent tests
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_start_conversation():
    """Test starting conversation"""
    from agents.sales_agent import SalesAgent
    from agents.lead_agent import LeadAgent
    sa = SalesAgent()
    la = LeadAgent(use_mock=True)
    leads = la.find_leads(platform='reddit')
    if leads:
        res = sa.start_conversation(leads[0]['id'])
        assert isinstance(res, dict)


def test_draft_first_message():
    """Test drafting first message"""
    from agents.sales_agent import SalesAgent
    from agents.lead_agent import LeadAgent
    sa = SalesAgent()
    la = LeadAgent(use_mock=True)
    leads = la.find_leads(platform='reddit')
    if leads:
        conv = sa.start_conversation(leads[0]['id'])
        if conv.get('conversation_id'):
            draft = sa.draft_first_message(leads[0]['id'], conv['conversation_id'])
            assert isinstance(draft, dict)


def test_process_customer_reply():
    """Test processing customer reply"""
    from agents.sales_agent import SalesAgent
    from agents.lead_agent import LeadAgent
    sa = SalesAgent()
    la = LeadAgent(use_mock=True)
    leads = la.find_leads(platform='reddit')
    if leads:
        conv = sa.start_conversation(leads[0]['id'])
        if conv.get('conversation_id'):
            res = sa.process_customer_reply(conv['conversation_id'], "I'm interested")
            assert isinstance(res, dict)


def test_negotiate_with_engine():
    """Test negotiation with discount engine validation"""
    from agents.sales_agent import SalesAgent
    from agents.lead_agent import LeadAgent
    from services.product_service import ProductService
    sa = SalesAgent()
    la = LeadAgent(use_mock=True)
    ps = ProductService()
    
    # Create product
    prod = ps.create_product(name="SaleTest", normal_price=100, minimum_price=40)
    if prod is None:
        prods = ps.get_all_products()
        prod = next((p for p in prods if p["name"] == "SaleTest"), None)
    
    leads = la.find_leads(platform='reddit')
    if leads and prod:
        conv = sa.start_conversation(leads[0]['id'])
        if conv.get('conversation_id'):
            # Valid discount
            res = sa.negotiate(conv['conversation_id'], prod['id'], proposed_discount=20)
            assert res['success'] is True
            # Invalid discount > 60
            res2 = sa.negotiate(conv['conversation_id'], prod['id'], proposed_discount=70)
            assert res2['success'] is False
        ps.delete_product(prod['id'])


def test_follow_up():
    """Test follow up suggestion"""
    from agents.sales_agent import SalesAgent
    from agents.lead_agent import LeadAgent
    sa = SalesAgent()
    la = LeadAgent(use_mock=True)
    leads = la.find_leads(platform='reddit')
    if leads:
        res = sa.follow_up(leads[0]['id'])
        assert isinstance(res, dict)
