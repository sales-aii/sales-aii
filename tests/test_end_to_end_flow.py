# -*- coding: utf-8 -*-
"""
End-to-end sales flow test.

Walks the whole pipeline with the mock AI provider and mocked platform HTTP:

    product -> leads -> AI analysis -> conversation -> draft
            -> [NOT sent until approved] -> negotiation
            -> customer reply -> analytics

Every business rule is asserted explicitly:
- nothing is sent without explicit approval
- >60% discount is rejected
- final price below minimum price is rejected
- %60 is a final offer and nothing may follow it
- an undefined discount code is rejected
- the AI cannot invent a discount code
- AI suggestions are re-validated by the discount engine
"""

import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
#: captured once - re-reading httpx.Client inside the patch would wrap the
#: already patched fake and the first transport would win
_REAL_CLIENT = httpx.Client


def _patch_client(monkeypatch, handler):
    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return _REAL_CLIENT(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


def _make_product(price=100.0, minimum=40.0, name="E2E Product"):
    from services.product_service import ProductService
    return ProductService().create_product(
        name=name, normal_price=price, minimum_price=minimum
    )


def _make_lead():
    from agents.lead_agent import LeadAgent
    leads = LeadAgent(use_mock=True).find_leads(platform='reddit')
    assert leads, "no lead discovered - the flow cannot be verified"
    return leads[0]


# ==========================================================================
# Happy path
# ==========================================================================
def test_full_sales_flow():
    from agents.lead_agent import LeadAgent
    from agents.sales_agent import SalesAgent
    from services.discount_engine import DiscountEngine
    from services.message_service import MessageService

    product = _make_product()
    assert product and product["id"], "product fixture failed"

    # --- 1. lead discovery -------------------------------------------------
    lead_agent = LeadAgent(use_mock=True)
    leads = lead_agent.find_leads(platform='reddit')
    assert len(leads) == 2
    lead_id = leads[0]['id']

    # --- 2. AI analysis ----------------------------------------------------
    analysis = lead_agent.analyze_lead(lead_id)
    assert analysis
    analyzed = lead_agent.lead_service.get_lead(lead_id)
    assert analyzed['status'] == 'analyzed'
    assert analyzed['lead_quality'] in ('Low', 'Medium', 'High')

    # --- 3. conversation ---------------------------------------------------
    sales = SalesAgent()
    conv = sales.start_conversation(lead_id)
    conv_id = conv['conversation_id']

    # --- 4. draft (must NOT be sent) ---------------------------------------
    draft = sales.draft_first_message(lead_id, conv_id)
    message_id = draft['message_id']

    messages = MessageService().get_messages(conv_id)
    stored = next(m for m in messages if m['id'] == message_id)
    assert stored['sent'] is False
    assert stored['approved'] is False

    # --- 5. negotiation with a legal discount ------------------------------
    negotiation = sales.negotiate(conv_id, product_id=product['id'],
                                  proposed_discount=20)
    assert negotiation['success'] is True
    validation = negotiation['validation']
    assert validation['final_price'] == pytest.approx(80.0)
    assert validation['is_final_offer'] is False

    # --- 6. approval then a real send --------------------------------------
    messages_service = MessageService()
    sent_payloads = []

    def sender(platform, recipient, content):
        sent_payloads.append(content)
        return {'success': True, 'external_message_id': 'ext-e2e'}

    messages_service.register_sender('reddit', sender)
    send_result = sales.approve_and_send(conv_id, message_id)
    assert send_result['success'] is True
    assert send_result['status'] == 'sent'
    assert sent_payloads, "the channel must actually receive the message"

    # --- 7. customer reply -> analyse + draft ------------------------------
    reply = sales.process_customer_reply(
        conv_id, "Çok pahalı, biraz düşüneyim, başka yerlere de bakacağım"
    )
    assert reply['analysis'], "reply must be analysed"
    assert reply['draft'], "a reply draft must be produced"
    assert reply['draft']['approved'] is False
    assert reply['draft']['sent'] is False

    # --- 8. discount engine still agrees -----------------------------------
    engine = DiscountEngine()
    assert engine.validate_discount(
        product['id'], 20, has_final_offer=False
    )['valid'] is True


# ==========================================================================
# Approval gate - the single most important rule
# ==========================================================================
def test_nothing_is_sent_without_explicit_approval():
    from agents.lead_agent import LeadAgent
    from agents.sales_agent import SalesAgent
    from services.message_service import MessageService

    lead_id = LeadAgent(use_mock=True).find_leads(platform='reddit')[0]['id']
    sales = SalesAgent()
    conv_id = sales.start_conversation(lead_id)['conversation_id']
    message_id = sales.draft_first_message(lead_id, conv_id)['message_id']

    ms = MessageService()
    delivered = []
    ms.register_sender(
        'reddit', lambda p, r, c: delivered.append(c) or {'success': True}
    )

    # attempt to send while unapproved
    result = ms.send(message_id)
    assert result['success'] is False
    assert delivered == [], "an unapproved message must never leave the app"

    # agent-level path is equally blocked
    agent_result = sales.approve_and_send(conv_id, message_id, approved=False)
    assert agent_result['success'] is True
    assert agent_result['status'] == 'rejected'
    assert delivered == []


# ==========================================================================
# Discount rules
# ==========================================================================
def test_discount_above_60_is_rejected():
    from agents.sales_agent import SalesAgent
    from services.discount_engine import DiscountEngine

    product = _make_product(name="Rule >60")
    engine = DiscountEngine()

    for percent in (60.1, 61, 75, 100, -5 + 200):
        result = engine.validate_discount(product['id'], percent)
        assert result['valid'] is False, f"{percent}% must be rejected"
        assert result['errors'], "a rejection must explain why"

    # the agent must surface the same rejection
    sales = SalesAgent()
    agent_result = sales.negotiate(1, product_id=product['id'],
                                   proposed_discount=80)
    assert agent_result['success'] is False
    assert agent_result['errors']


def test_final_price_below_minimum_is_rejected():
    from services.discount_engine import DiscountEngine

    # 60% of 100 = 40 which equals minimum_price -> allowed
    product = _make_product(price=100.0, minimum=40.0, name="Rule min ok")
    engine = DiscountEngine()
    assert engine.validate_discount(product['id'], 60)['valid'] is True

    # raise the minimum above the discounted price -> must be rejected
    product2 = _make_product(price=100.0, minimum=90.0, name="Rule min fail")
    result = engine.validate_discount(product2['id'], 60)
    assert result['valid'] is False
    assert 'minimum' in result['errors'][0].lower() or \
        'minimum_price' in result['errors'][0]


def test_60_percent_is_a_final_offer():
    from services.discount_engine import DiscountEngine

    product = _make_product(name="Rule final")
    engine = DiscountEngine()

    result = engine.validate_discount(product['id'], 60)
    assert result['valid'] is True
    assert result.get('is_final_offer') is True

    # nothing may follow a final offer
    after = engine.validate_discount(product['id'], 10, has_final_offer=True)
    assert after['valid'] is False
    assert after['errors']


def test_after_final_offer_even_zero_discount_is_blocked():
    from agents.sales_agent import SalesAgent

    product = _make_product(name="Rule after final")
    lead_id = _make_lead()['id']
    sales = SalesAgent()
    conv_id = sales.start_conversation(lead_id)['conversation_id']

    final = sales.negotiate(conv_id, product_id=product['id'],
                            proposed_discount=60)
    assert final['success'] is True
    assert final['validation']['is_final_offer'] is True

    following = sales.negotiate(conv_id, product_id=product['id'],
                               proposed_discount=5)
    assert following['success'] is False, \
        "no discount may be offered after the %60 final offer"


def test_undefined_discount_code_is_rejected():
    from services.discount_engine import DiscountEngine

    product = _make_product(name="Rule code")
    result = DiscountEngine().validate_discount(
        product['id'], 10, discount_code="NOT_A_REAL_CODE"
    )
    assert result['valid'] is False
    assert result['errors']


def test_active_discount_code_is_accepted(monkeypatch):
    from repositories.discount_code_repository import DiscountCodeRepository
    from database.database import db
    from services.discount_engine import DiscountEngine

    product = _make_product(name="Rule code active")
    with db.session_scope() as session:
        DiscountCodeRepository().create(
            session,
            code="REAL10",
            discount_percent=10,
            product_id=product['id'],
            active=True,
        )

    result = DiscountEngine().validate_discount(
        product['id'], 10, discount_code="REAL10"
    )
    assert result['valid'] is True, result['errors']


def test_inactive_discount_code_is_rejected():
    from repositories.discount_code_repository import DiscountCodeRepository
    from database.database import db
    from services.discount_engine import DiscountEngine

    product = _make_product(name="Rule code inactive")
    with db.session_scope() as session:
        DiscountCodeRepository().create(
            session,
            code="DEAD",
            discount_percent=10,
            product_id=product['id'],
            active=False,
        )

    result = DiscountEngine().validate_discount(
        product['id'], 10, discount_code="DEAD"
    )
    assert result['valid'] is False


def test_discount_code_percentage_must_match():
    from repositories.discount_code_repository import DiscountCodeRepository
    from database.database import db
    from services.discount_engine import DiscountEngine

    product = _make_product(name="Rule code mismatch")
    with db.session_scope() as session:
        DiscountCodeRepository().create(
            session,
            code="TEN",
            discount_percent=10,
            product_id=product['id'],
            active=True,
        )

    result = DiscountEngine().validate_discount(
        product['id'], 25, discount_code="TEN"
    )
    assert result['valid'] is False


def test_ai_cannot_create_a_discount_code(monkeypatch):
    """
    The AI may suggest a discount but never a code. Any code coming from the
    model has to exist in the database already.
    """
    from agents.sales_agent import SalesAgent

    product = _make_product(name="Rule ai code")
    lead_id = _make_lead()['id']
    sales = SalesAgent()
    conv_id = sales.start_conversation(lead_id)['conversation_id']

    # the model "invented" a code
    hallucinated = sales.negotiate(conv_id, product_id=product['id'],
                                   proposed_discount=10,
                                   discount_code="AI_MADE_THIS_UP")
    assert hallucinated['success'] is False

    # and no code row was created as a side effect
    from repositories.discount_code_repository import DiscountCodeRepository
    from database.database import db
    with db.session_scope() as session:
        codes = DiscountCodeRepository().get_all(session)
    assert not any(c.code == "AI_MADE_THIS_UP" for c in codes)


def test_ai_suggested_discount_is_revalidated_by_the_backend(monkeypatch):
    """
    Even if the AI "decides" to give 80%, the engine must reject it.
    """
    from agents.sales_agent import SalesAgent

    product = _make_product(name="Rule ai over")
    lead_id = _make_lead()['id']
    sales = SalesAgent()
    conv_id = sales.start_conversation(lead_id)['conversation_id']

    monkeypatch.setattr(
        sales.ai_manager, 'generate_structured_response',
        lambda *a, **kw: {
            'recommended_discount_level': 80,
            'draft_message': 'here is 80% off!',
        }
    )
    result = sales.negotiate(conv_id, product_id=product['id'],
                             proposed_discount=80)
    assert result['success'] is False


def test_negotiation_engine_respects_the_same_rules():
    from services.negotiation_engine import NegotiationEngine

    product = _make_product(price=100.0, minimum=40.0, name="Rule neg engine")
    engine = NegotiationEngine()

    # weak signal -> low opening discount
    assert engine.determine_discount('pahalı', True) == 10

    step = engine.negotiate_step(
        product_id=product['id'], conversation_id=1,
        buying_signal='want to buy but', price_objection=True,
    )
    assert step['success'] is True
    assert 0 < step['proposed_discount'] <= 60

    # an illegal proposal cannot slip through the engine either
    illegal = engine.negotiate_step(
        product_id=product['id'], conversation_id=1,
        buying_signal='', price_objection=False,
        proposed_discount=90,
    )
    assert illegal['success'] is False
    assert illegal['errors']


# ==========================================================================
# Platform failures never become fake results
# ==========================================================================
def test_shopier_payment_needs_real_confirmation(monkeypatch):
    from integrations.shopier import ShopierIntegration

    monkeypatch.setattr("integrations.shopier.settings.SHOPIER_API_TOKEN", "PAT")

    def unpaid(request):
        return httpx.Response(
            200, json={"data": {"id": "e2e", "paymentStatus": "unpaid"}}
        )

    _patch_client(monkeypatch, unpaid)
    result = ShopierIntegration().verify_payment({"orderId": "e2e"})
    assert result['verified'] is False
    assert result['status'] == 'pending'

    def paid(request):
        return httpx.Response(
            200, json={"data": {"id": "e2e", "paymentStatus": "paid"}}
        )

    _patch_client(monkeypatch, paid)
    result = ShopierIntegration().verify_payment({"orderId": "e2e"})
    assert result['verified'] is True


def test_telegram_failure_is_reported(monkeypatch):
    from integrations.telegram import TelegramIntegration

    monkeypatch.setattr("integrations.telegram.settings.TELEGRAM_BOT_TOKEN", "T")
    monkeypatch.setattr("integrations.telegram.settings.TELEGRAM_CHAT_ID", "1")

    def handler(request):
        return httpx.Response(200, json={"ok": False, "description": "blocked"})

    _patch_client(monkeypatch, handler)
    from utils.exceptions import APIError
    with pytest.raises(APIError):
        TelegramIntegration().send_message("hi")
    assert TelegramIntegration().try_notify("hi") is False


# ==========================================================================
# Analytics reflect real rows only
# ==========================================================================
def test_analytics_counts_only_real_records():
    from agents.analytics import Analytics

    _make_product(name="Analytics Product")
    lead_id = _make_lead()['id']
    assert lead_id

    metrics = Analytics().get_metrics()
    # the mock reddit fixture produces exactly two leads
    assert metrics['total_leads'] == 2
    assert metrics['leads_today'] == 2
    assert metrics['sales'] == 0
    assert metrics['revenue'] == 0.0
    assert metrics['offers'] == 0
    assert metrics['conversion_rate'] == 0.0


def test_analytics_reports_a_broken_database(monkeypatch):
    """A failing query must not be reported as an empty database"""
    from agents.analytics import Analytics
    from utils.exceptions import DatabaseError

    analytics = Analytics()

    def boom():
        raise RuntimeError("database is locked")

    monkeypatch.setattr(analytics.db, "session_scope", boom)
    with pytest.raises(DatabaseError):
        analytics.get_metrics()


def test_analytics_insights_surface_ai_failures(monkeypatch):
    """An AI outage must not be reported as 'insufficient data'"""
    from agents.analytics import Analytics
    from utils.exceptions import APIError

    analytics = Analytics()

    def boom(*a, **kw):
        raise APIError("provider down")

    monkeypatch.setattr(analytics, "get_metrics", lambda: {'total_leads': 0})
    monkeypatch.setattr(
        "ai.ai_manager.AIManager.generate_structured_response", boom
    )
    with pytest.raises(APIError):
        analytics.generate_insights()