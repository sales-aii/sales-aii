# -*- coding: utf-8 -*-
"""
Lead agent tests.

Every assertion here must actually execute - no `if leads:` guards, so a test
can never silently pass because the fixture returned nothing.
"""

import sys
from pathlib import Path

import httpx
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.exceptions import APIError  # noqa: E402


def _patch_client(monkeypatch, handler):
    real_client_cls = httpx.Client

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", fake_client)


# ==========================================================================
# Lead discovery through the mock (offline)
# ==========================================================================
def test_find_leads_reddit_creates_leads():
    from agents.lead_agent import LeadAgent
    agent = LeadAgent(use_mock=True)
    leads = agent.find_leads(platform='reddit')
    assert len(leads) == 2, "mock reddit must yield 2 leads"
    assert agent.last_errors == {}
    assert {lead['platform'] for lead in leads} == {'reddit'}


def test_find_leads_github_creates_leads():
    from agents.lead_agent import LeadAgent
    agent = LeadAgent(use_mock=True)
    leads = agent.find_leads(platform='github')
    assert len(leads) == 2, "mock github must yield 2 leads"
    assert agent.last_errors == {}


def test_find_leads_all_platforms():
    from agents.lead_agent import LeadAgent
    agent = LeadAgent(use_mock=True)
    leads = agent.find_leads()
    assert len(leads) == 4
    platforms = {lead['platform'] for lead in leads}
    assert platforms == {'reddit', 'github'}


def test_duplicate_leads_are_skipped():
    """A second run must not create the same leads again"""
    from agents.lead_agent import LeadAgent
    agent = LeadAgent(use_mock=True)
    first = agent.find_leads(platform='reddit')
    second = agent.find_leads(platform='reddit')
    assert len(first) == 2
    assert second == [], "duplicates must be filtered out"


def test_same_user_different_posts_are_separate_leads():
    """
    The duplicate key is the source URL, not the username: one user can post
    several distinct needs.
    """
    from agents.lead_agent import LeadAgent
    agent = LeadAgent(use_mock=True)
    base = {
        'platform': 'reddit',
        'username': 'multi_poster',
        'need': 'need',
    }
    first = agent._save_lead_if_new({
        **base, 'platform_id': 'p1',
        'source_url': 'https://reddit.com/comments/p1',
    })
    second = agent._save_lead_if_new({
        **base, 'platform_id': 'p2',
        'source_url': 'https://reddit.com/comments/p2',
    })
    repeat = agent._save_lead_if_new({
        **base, 'platform_id': 'p2',
        'source_url': 'https://reddit.com/comments/p2',
    })
    assert first is not None
    assert second is not None
    assert repeat is None, "the exact same post must be deduplicated"


def test_lead_without_platform_is_skipped():
    from agents.lead_agent import LeadAgent
    agent = LeadAgent(use_mock=True)
    assert agent._save_lead_if_new({'username': 'x', 'source_url': 'u'}) is None


# ==========================================================================
# Normalisation of real API payloads
# ==========================================================================
def test_normalize_real_reddit_payload():
    from agents.lead_agent import LeadAgent
    post = {
        'id': 'abc123',
        'title': 'Looking for a tool',
        'selftext': 'I need automation',
        'author': 'alice',
        'permalink': '/r/python/comments/abc123/looking/',
        'subreddit': 'python',
    }
    lead = LeadAgent._normalize_reddit_post(post)
    assert lead['username'] == 'alice'
    assert lead['platform_id'] == 'abc123'
    assert lead['source_url'] == \
        'https://www.reddit.com/r/python/comments/abc123/looking/'
    assert lead['need_description'] == 'I need automation'
    assert lead['profile_url'] == 'https://reddit.com/u/alice'


def test_normalize_real_github_payload():
    from agents.lead_agent import LeadAgent
    issue = {
        'number': 42,
        'title': 'Feature request',
        'body': 'Please add dark mode',
        'html_url': 'https://github.com/octocat/repo/issues/42',
        'user': {'login': 'octocat'},
    }
    lead = LeadAgent._normalize_github_issue(issue)
    assert lead['username'] == 'octocat'
    assert lead['platform_id'] == 42
    assert lead['need_description'] == 'Please add dark mode'
    assert lead['profile_url'] == 'https://github.com/octocat'


def test_normalize_tolerates_missing_github_user():
    from agents.lead_agent import LeadAgent
    lead = LeadAgent._normalize_github_issue({'number': 1, 'title': 't'})
    assert lead['username'] is None
    assert lead['profile_url'] is None


# ==========================================================================
# Real API path - failures must be reported, never faked
# ==========================================================================
def test_real_mode_reports_error_instead_of_faking_leads(monkeypatch):
    """use_mock=False with no credentials must not invent leads"""
    from agents.lead_agent import LeadAgent

    agent = LeadAgent(use_mock=False)
    leads = agent.find_leads(platform='reddit')
    assert leads == []
    assert 'reddit' in agent.last_errors
    assert 'REDDIT_CLIENT_ID' in agent.last_errors['reddit']


def test_real_mode_saves_leads_from_reddit_api(monkeypatch):
    from agents.lead_agent import LeadAgent
    from integrations.reddit import RedditIntegration

    monkeypatch.setattr("integrations.reddit.settings.REDDIT_CLIENT_ID", "CID")
    monkeypatch.setattr("integrations.reddit.settings.REDDIT_CLIENT_SECRET", "SEC")

    def handler(request: httpx.Request):
        if str(request.url) == RedditIntegration.TOKEN_URL:
            return httpx.Response(200, json={"access_token": "T",
                                            "expires_in": 3600})
        return httpx.Response(200, json={"data": {"children": [{
            "data": {
                "id": "zz999",
                "title": "need a bot",
                "selftext": "please",
                "author": "realuser",
                "permalink": "/r/test/comments/zz999/need_a_bot/",
            }
        }]}})

    _patch_client(monkeypatch, handler)

    agent = LeadAgent(use_mock=False)
    leads = agent.find_leads(platform='reddit', queries=['need a bot'])
    assert len(leads) == 1
    assert leads[0]['username'] == 'realuser'
    assert agent.last_errors == {}


def test_real_mode_api_failure_is_recorded(monkeypatch):
    from agents.lead_agent import LeadAgent
    from integrations.reddit import RedditIntegration

    monkeypatch.setattr("integrations.reddit.settings.REDDIT_CLIENT_ID", "CID")
    monkeypatch.setattr("integrations.reddit.settings.REDDIT_CLIENT_SECRET", "SEC")

    def handler(request: httpx.Request):
        if str(request.url) == RedditIntegration.TOKEN_URL:
            return httpx.Response(200, json={"access_token": "T",
                                            "expires_in": 3600})
        return httpx.Response(503, json={"message": "Service Unavailable"})

    _patch_client(monkeypatch, handler)

    agent = LeadAgent(use_mock=False)
    leads = agent.find_leads(platform='reddit', queries=['x'])
    assert leads == []
    assert '503' in agent.last_errors['reddit']


def test_auto_mode_uses_real_when_configured(monkeypatch):
    from agents.lead_agent import LeadAgent
    monkeypatch.setattr("integrations.reddit.settings.REDDIT_CLIENT_ID", "CID")
    monkeypatch.setattr("integrations.reddit.settings.REDDIT_CLIENT_SECRET", "SEC")
    agent = LeadAgent()  # use_mock=None -> auto
    assert agent.using_mock('reddit') is False


def test_auto_mode_falls_back_to_mock_when_unconfigured(monkeypatch):
    from agents.lead_agent import LeadAgent
    monkeypatch.setattr("integrations.reddit.settings.REDDIT_CLIENT_ID", None)
    monkeypatch.setattr("integrations.reddit.settings.REDDIT_CLIENT_SECRET", None)
    agent = LeadAgent()
    assert agent.using_mock('reddit') is True


def test_unsupported_platform_raises():
    from agents.lead_agent import LeadAgent
    agent = LeadAgent(use_mock=True)
    with pytest.raises(APIError):
        agent._get_integration('myspace')


# ==========================================================================
# AI analysis
# ==========================================================================
def test_analyze_lead_updates_record():
    from agents.lead_agent import LeadAgent
    agent = LeadAgent(use_mock=True)
    leads = agent.find_leads(platform='reddit')
    assert leads, "no leads created - the assertions below would be skipped"

    lead_id = leads[0]['id']
    result = agent.analyze_lead(lead_id)
    assert isinstance(result, dict) and result

    updated = agent.lead_service.get_lead(lead_id)
    assert updated['status'] == 'analyzed'
    assert updated['lead_quality'] in ('Low', 'Medium', 'High')


def test_analyze_lead_raises_for_missing_lead():
    from agents.lead_agent import LeadAgent
    agent = LeadAgent(use_mock=True)
    with pytest.raises(APIError):
        agent.analyze_lead(999999)


def test_analyze_lead_raises_when_ai_fails(monkeypatch):
    """An AI failure must surface, not return {} as if nothing happened"""
    from agents.lead_agent import LeadAgent

    agent = LeadAgent(use_mock=True)
    leads = agent.find_leads(platform='reddit')
    assert leads

    def boom(*a, **kw):
        raise APIError("provider down")

    monkeypatch.setattr(agent.ai_manager, 'generate_structured_response', boom)
    with pytest.raises(APIError):
        agent.analyze_lead(leads[0]['id'])


def test_product_match_is_validated_against_catalogue():
    from agents.lead_agent import LeadAgent
    products = [{'id': 1}, {'id': 7}]
    validate = LeadAgent._validate_product_match
    assert validate(7, products) == 7
    assert validate("7", products) == 7
    assert validate(99, products) is None      # hallucinated id
    assert validate("Dark Mode Pro", products) is None  # name, not id
    assert validate(None, products) is None