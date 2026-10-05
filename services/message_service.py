# -*- coding: utf-8 -*-
"""
Message service - single owner of the draft / approve / send workflow.

Sending rules:
- a message must be explicitly approved by the user before it can be sent
- a send only succeeds when a real outbound channel exists for the platform
- if no channel can deliver the message, the failure is reported and the
  message stays unsent - it is never marked as sent
"""

from typing import Any, Callable, Dict, List, Optional

from services.base_service import BaseService
from repositories.message_repository import MessageRepository
from repositories.conversation_repository import ConversationRepository


#: A sender receives (platform, recipient_url, content) and returns a dict with
#: at least {"success": bool, "external_message_id": str | None}
Sender = Callable[[str, Optional[str], str], Dict[str, Any]]


class MessageService(BaseService):
    """Message service with approval workflow"""

    #: Shared platform -> sender registry.
    #: Deliberately class level: an outbound channel is app configuration, not
    #: per-instance state, so a channel registered once is visible to every
    #: service and agent instance. Empty by default - Sales.aii ships no
    #: outbound sales channel, and inventing one is not allowed.
    _senders: Dict[str, Sender] = {}

    def __init__(self):
        super().__init__()
        self.msg_repo = MessageRepository()
        self.conv_repo = ConversationRepository()

    # ------------------------------------------------------------------
    # Outbound channel registry
    # ------------------------------------------------------------------
    @classmethod
    def register_sender(cls, platform: str, sender: Sender) -> None:
        """Register a real outbound sender for a platform"""
        if not callable(sender):
            raise ValueError("sender must be callable")
        cls._senders[platform] = sender

    @classmethod
    def unregister_sender(cls, platform: str) -> None:
        cls._senders.pop(platform, None)

    @classmethod
    def has_sender(cls, platform: Optional[str]) -> bool:
        return bool(platform) and platform in cls._senders

    @classmethod
    def available_platforms(cls) -> List[str]:
        return list(cls._senders)

    # ------------------------------------------------------------------
    # Draft lifecycle
    # ------------------------------------------------------------------
    def create_draft(self, conversation_id: int, content: str,
                     sender: str = 'agent') -> Optional[Dict]:
        """Create draft message (not sent, not approved)"""
        if not content or not content.strip():
            self.logger.warning("Refusing to create an empty draft")
            return None
        try:
            with self.db.session_scope() as session:
                msg = self.msg_repo.create(
                    session,
                    conversation_id=conversation_id,
                    sender=sender,
                    content=content,
                    message_type='text',
                    status='pending',
                    approved=False,
                    sent=False
                )
                return {
                    'id': msg.id,
                    'content': msg.content,
                    'status': msg.status,
                    'approved': False,
                    'sent': False,
                }
        except Exception as e:
            self.logger.error(f"Create draft error: {e}")
            return None

    def update_draft(self, message_id: int, content: str) -> bool:
        """Update draft content (only while it has not been sent)"""
        if not content or not content.strip():
            return False
        try:
            with self.db.session_scope() as session:
                msg = self.msg_repo.get_by_id(session, message_id)
                if not msg or msg.sent:
                    return False
                self.msg_repo.update(session, msg, content=content)
                return True
        except Exception as e:
            self.logger.error(f"Update draft error: {e}")
            return False

    def approve(self, message_id: int) -> Dict[str, Any]:
        """Mark a message as approved by the user (does not send it)"""
        try:
            with self.db.session_scope() as session:
                msg = self.msg_repo.get_by_id(session, message_id)
                if not msg:
                    return {'success': False, 'error': 'Message not found'}
                if msg.sent:
                    return {'success': False, 'error': 'Message was already sent'}
                msg.approved = True
                msg.status = 'approved'
                return {'success': True, 'status': 'approved'}
        except Exception as e:
            self.logger.error(f"Approve error: {e}")
            return {'success': False, 'error': str(e)}

    def reject(self, message_id: int) -> Dict[str, Any]:
        """Reject a message - it will never be sent"""
        try:
            with self.db.session_scope() as session:
                msg = self.msg_repo.get_by_id(session, message_id)
                if not msg:
                    return {'success': False, 'error': 'Message not found'}
                if msg.sent:
                    return {'success': False, 'error': 'Message was already sent'}
                msg.approved = False
                msg.sent = False
                msg.status = 'rejected'
                return {'success': True, 'status': 'rejected'}
        except Exception as e:
            self.logger.error(f"Reject error: {e}")
            return {'success': False, 'error': str(e)}

    def send(self, message_id: int) -> Dict[str, Any]:
        """
        Send an approved message through the platform's real channel.

        Returns success only when a channel exists AND the channel confirmed
        delivery. Otherwise the message is marked failed and stays unsent.
        """
        try:
            with self.db.session_scope() as session:
                msg = self.msg_repo.get_by_id(session, message_id)
                if not msg:
                    return {'success': False, 'error': 'Message not found',
                            'status': 'failed'}
                if msg.sent:
                    return {'success': False, 'error': 'Message was already sent',
                            'status': 'sent'}
                if not msg.approved:
                    self.logger.warning(
                        f"Blocked send of unapproved message {message_id}"
                    )
                    return {'success': False,
                            'error': 'Message not approved by user',
                            'status': 'pending'}

                platform = msg.platform or self._platform_of(session, msg)
                content = msg.content

            sender = self._senders.get(platform) if platform else None
            if sender is None:
                reason = (
                    f"No outbound channel configured for '{platform}'. "
                    "Sales.aii will not mark a message as sent when nothing "
                    "was actually delivered."
                )
                self._mark_failed(message_id)
                self.logger.error(reason)
                return {'success': False, 'error': reason, 'status': 'failed'}

            result = sender(platform, None, content) or {}
            if not result.get('success'):
                self._mark_failed(message_id)
                error = result.get('error') or 'Platform send failed'
                self.logger.error(f"Send failed for message {message_id}: {error}")
                return {'success': False, 'error': error, 'status': 'failed'}

            with self.db.session_scope() as session:
                msg = self.msg_repo.get_by_id(session, message_id)
                msg.sent = True
                msg.status = 'sent'
                msg.external_message_id = result.get('external_message_id')
                return {
                    'success': True,
                    'status': 'sent',
                    'external_message_id': msg.external_message_id,
                }
        except Exception as e:
            self._mark_failed(message_id)
            self.logger.error(f"Send error: {e}")
            return {'success': False, 'error': str(e), 'status': 'failed'}

    def approve_and_send(self, message_id: int) -> Dict[str, Any]:
        """Approve and send in one step (used by the UI approve button)"""
        approved = self.approve(message_id)
        if not approved.get('success'):
            return approved
        return self.send(message_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _platform_of(self, session, msg) -> Optional[str]:
        """Resolve the platform from the parent conversation"""
        try:
            conv = self.conv_repo.get_by_id(session, msg.conversation_id)
            return conv.platform if conv else None
        except Exception as e:
            self.logger.error(f"Could not resolve conversation platform: {e}")
            return None

    def _mark_failed(self, message_id: int) -> None:
        try:
            with self.db.session_scope() as session:
                msg = self.msg_repo.get_by_id(session, message_id)
                if msg and not msg.sent:
                    msg.sent = False
                    msg.status = 'failed'
        except Exception as e:
            self.logger.error(f"Could not mark message {message_id} as failed: {e}")

    def get_messages(self, conversation_id: int) -> List[Dict]:
        try:
            with self.db.session_scope() as session:
                msgs = self.msg_repo.get_by_conversation_id(session, conversation_id)
                return [{
                    'id': m.id,
                    'sender': m.sender,
                    'content': m.content,
                    'status': m.status,
                    'approved': m.approved,
                    'sent': m.sent,
                    'external_message_id': m.external_message_id,
                    'created_at': m.created_at
                } for m in msgs]
        except Exception as e:
            self.logger.error(f"Get messages error: {e}")
            return []