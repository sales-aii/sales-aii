# -*- coding: utf-8 -*-
"""
Support agent and analytics tests.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.exceptions import APIError  # noqa: E402


# ==========================================================================
# Support agent
# ==========================================================================
def test_support_returns_a_decision():
    from agents.support_agent import SupportAgent
    result = SupportAgent().process_ticket({'inquiry': 'How does this work?'})
    assert isinstance(result, dict)
    assert 'owner_intervention_required' in result
    assert isinstance(result['owner_intervention_required'], bool)
    assert isinstance(result['confidence'], float)


def test_low_confidence_escalates_to_owner():
    from agents.support_agent import SupportAgent
    agent = SupportAgent()
    monkey = agent.ai_manager.generate_structured_response
    agent.ai_manager.generate_structured_response = lambda *a, **kw: {
        'confidence': 0.1, 'suggested_response': 'not sure'
    }
    result = agent.process_ticket({'inquiry': 'weird issue'})
    assert result['owner_intervention_required'] is True
    agent.ai_manager.generate_structured_response = monkey


def test_explicit_owner_request_escalates():
    from agents.support_agent import SupportAgent
    agent = SupportAgent()
    agent.ai_manager.generate_structured_response = lambda *a, **kw: {
        'confidence': 0.99, 'needs_owner_intervention': True
    }
    result = agent.process_ticket({'inquiry': 'refund please'})
    assert result['owner_intervention_required'] is True


def test_non_numeric_confidence_escalates():
    """An unparseable confidence must not silently disable escalation"""
    from agents.support_agent import SupportAgent
    agent = SupportAgent()
    agent.ai_manager.generate_structured_response = lambda *a, **kw: {
        'confidence': 'high', 'suggested_response': 'x'
    }
    result = agent.process_ticket({'inquiry': 'x'})
    assert result['owner_intervention_required'] is True
    assert result['confidence'] == 0.0


def test_support_reports_ai_failure(monkeypatch):
    """An AI outage must not be disguised as 'needs the owner'"""
    from agents.support_agent import SupportAgent
    agent = SupportAgent()

    def boom(*a, **kw):
        raise APIError("provider down")

    monkeypatch.setattr(agent.ai_manager, 'generate_structured_response', boom)
    with pytest.raises(APIError):
        agent.process_ticket({'inquiry': 'anything'})


def test_support_rejects_empty_ticket():
    from agents.support_agent import SupportAgent
    with pytest.raises(APIError):
        SupportAgent().process_ticket({})


def test_support_unknown_product_raises():
    from agents.support_agent import SupportAgent
    with pytest.raises(APIError):
        SupportAgent().process_ticket(
            {'inquiry': 'hi', 'product_id': 999999}
        )


def test_support_handle_ticket_carries_id():
    from agents.support_agent import SupportAgent
    result = SupportAgent().handle_ticket(
        ticket_id=42, ticket_data={'inquiry': 'hello'}
    )
    assert result['ticket_id'] == 42


# ==========================================================================
# Analytics
# ==========================================================================
def test_analytics_metrics_keys():
    from agents.analytics import Analytics
    m = Analytics().get_metrics()
    for key in ('total_leads', 'leads_today', 'replies', 'offers', 'sales',
                'revenue', 'conversion_rate', 'average_discount'):
        assert key in m, f"missing metric '{key}'"
    assert isinstance(m['total_leads'], int)
    assert isinstance(m['revenue'], float)


def test_analytics_metrics_are_zero_on_an_empty_database():
    from agents.analytics import Analytics
    m = Analytics().get_metrics()
    assert m['total_leads'] == 0
    assert m['sales'] == 0
    assert m['revenue'] == 0.0
    assert m['conversion_rate'] == 0.0


def test_analytics_recent_activity():
    from agents.analytics import Analytics
    assert Analytics().get_recent_activity() == []


def test_analytics_insights_returns_real_ai_output():
    from agents.analytics import Analytics
    insights = Analytics().generate_insights()
    assert isinstance(insights, dict)
    assert insights, "the mock provider must return an actual payload"
