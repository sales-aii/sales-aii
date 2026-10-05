# -*- coding: utf-8 -*-
"""
Approval workflow tests.

No assertion here is guarded by an `if ...:` - a test must never pass just
because the setup produced no data.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.exceptions import APIError  # noqa: E402


def _new_draft():
    """Run the real lead -> conversation -> draft flow, return the ids"""
    from agents.lead_agent import LeadAgent
    from agents.sales_agent import SalesAgent
    from services.message_service import MessageService

    la = LeadAgent(use_mock=True)
    leads = la.find_leads(platform='reddit')
    assert len(leads) == 2, "mock reddit must produce leads"

    sa = SalesAgent()
    ms = MessageService()
    conv = sa.start_conversation(leads[0]['id'])
    assert conv.get('conversation_id')

    draft = sa.draft_first_message(leads[0]['id'], conv['conversation_id'])
    assert draft.get('message_id'), "AI draft was not stored"

    return sa, ms, conv['conversation_id'], draft['message_id']


# ==========================================================================
# Drafts are inert until approved
# ==========================================================================
def test_draft_is_created_unapproved_and_unsent():
    _sa, ms, _conv_id, message_id = _new_draft()
    msgs = ms.get_messages(1)
    draft = next(m for m in msgs if m['id'] == message_id)
    assert draft['sent'] is False
    assert draft['approved'] is False
    assert draft['status'] == 'pending'


def test_empty_draft_is_refused():
    from services.message_service import MessageService
    ms = MessageService()
    assert ms.create_draft(1, "   ") is None


def test_send_is_blocked_without_approval():
    _sa, ms, _conv_id, message_id = _new_draft()
    res = ms.send(message_id)
    assert res['success'] is False
    assert 'not approved' in res['error']
    assert res['status'] == 'pending'


def test_send_without_channel_reports_failure_honestly():
    """
    Sales.aii ships no outbound sales channel, so a send cannot succeed.
    The message must NOT be marked as sent.
    """
    _sa, ms, conv_id, message_id = _new_draft()
    ms.approve(message_id)
    res = ms.send(message_id)
    assert res['success'] is False
    assert res['status'] == 'failed'
    assert 'No outbound channel' in res['error']

    draft = next(m for m in ms.get_messages(conv_id) if m['id'] == message_id)
    assert draft['sent'] is False, "nothing was delivered, so it cannot be 'sent'"
    assert draft['status'] == 'failed'


# ==========================================================================
# Success path - only with a real registered channel
# ==========================================================================
def test_send_succeeds_when_a_channel_delivers():
    _sa, ms, conv_id, message_id = _new_draft()
    calls = []

    def sender(platform, recipient, content):
        calls.append((platform, content))
        return {'success': True, 'external_message_id': 'ext-123'}

    ms.register_sender('reddit', sender)
    assert ms.has_sender('reddit') is True

    res = ms.approve_and_send(message_id)
    assert res['success'] is True
    assert res['status'] == 'sent'
    assert res['external_message_id'] == 'ext-123'
    assert len(calls) == 1, "the channel must actually receive the message"

    draft = next(m for m in ms.get_messages(conv_id) if m['id'] == message_id)
    assert draft['sent'] is True
    assert draft['approved'] is True
    assert draft['external_message_id'] == 'ext-123'


def test_send_marks_failed_when_channel_errors():
    _sa, ms, _conv_id, message_id = _new_draft()

    def sender(platform, recipient, content):
        return {'success': False, 'error': 'channel rejected the payload'}

    ms.register_sender('reddit', sender)
    res = ms.approve_and_send(message_id)
    assert res['success'] is False
    assert res['error'] == 'channel rejected the payload'
    assert res['status'] == 'failed'


def test_double_send_is_refused():
    _sa, ms, _conv_id, message_id = _new_draft()
    ms.register_sender('reddit', lambda p, r, c: {'success': True})
    assert ms.approve_and_send(message_id)['success'] is True
    second = ms.send(message_id)
    assert second['success'] is False
    assert 'already sent' in second['error']


def test_register_sender_requires_callable():
    from services.message_service import MessageService
    ms = MessageService()
    for bad in (None, "not callable", 42):
        try:
            ms.register_sender('reddit', bad)
        except ValueError:
            continue
        raise AssertionError(f"register_sender accepted {bad!r}")


# ==========================================================================
# Approve / reject / edit
# ==========================================================================
def test_reject_marks_message_rejected():
    _sa, ms, conv_id, message_id = _new_draft()
    res = ms.reject(message_id)
    assert res['success'] is True
    assert res['status'] == 'rejected'

    draft = next(m for m in ms.get_messages(conv_id) if m['id'] == message_id)
    assert draft['sent'] is False
    assert draft['approved'] is False

    # a rejected message can still not be sent without re-approval
    ms.register_sender('reddit', lambda p, r, c: {'success': True})
    assert ms.send(message_id)['success'] is False


def test_update_draft_content():
    _sa, ms, conv_id, message_id = _new_draft()
    assert ms.update_draft(message_id, 'Updated content') is True
    draft = next(m for m in ms.get_messages(conv_id) if m['id'] == message_id)
    assert draft['content'] == 'Updated content'


def test_sent_message_cannot_be_edited():
    _sa, ms, _conv_id, message_id = _new_draft()
    ms.register_sender('reddit', lambda p, r, c: {'success': True})
    ms.approve_and_send(message_id)
    assert ms.update_draft(message_id, 'tampering') is False


def test_empty_update_is_refused():
    _sa, ms, _conv_id, message_id = _new_draft()
    assert ms.update_draft(message_id, '') is False


def test_unknown_message_is_reported():
    from services.message_service import MessageService
    ms = MessageService()
    assert ms.approve(999999)['success'] is False
    assert ms.reject(999999)['success'] is False
    assert ms.send(999999)['success'] is False


# ==========================================================================
# SalesAgent delegates to MessageService (single implementation)
# ==========================================================================
def test_sales_agent_rejects_message_from_another_conversation():
    sa, ms, _conv_id, message_id = _new_draft()
    res = sa.approve_and_send(9999, message_id)
    assert res['success'] is False
    assert 'does not belong' in res['error']


def test_sales_agent_reject_path():
    sa, _ms, conv_id, message_id = _new_draft()
    res = sa.approve_and_send(conv_id, message_id, approved=False)
    assert res['success'] is True
    assert res['status'] == 'rejected'


def test_sales_agent_send_without_channel_is_honest():
    sa, _ms, conv_id, message_id = _new_draft()
    res = sa.approve_and_send(conv_id, message_id)
    assert res['success'] is False
    assert 'No outbound channel' in res['error']


def test_sales_agent_start_conversation_reuses_active_one():
    from agents.lead_agent import LeadAgent
    from agents.sales_agent import SalesAgent

    la = LeadAgent(use_mock=True)
    lead_id = la.find_leads(platform='reddit')[0]['id']
    sa = SalesAgent()

    first = sa.start_conversation(lead_id)
    second = sa.start_conversation(lead_id)
    assert first['reused'] is False
    assert second['reused'] is True
    assert second['conversation_id'] == first['conversation_id']


def test_sales_agent_start_conversation_unknown_lead():
    from agents.sales_agent import SalesAgent
    with pytest.raises(APIError):
        SalesAgent().start_conversation(999999)