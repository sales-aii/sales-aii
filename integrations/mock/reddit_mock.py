# -*- coding: utf-8 -*-
"""
Mock Reddit integration for testing
"""

from typing import List, Dict, Any


class MockRedditIntegration:
    """Mock Reddit for unit tests - no real API calls"""

    def __init__(self):
        self.platform = "reddit"

    def search_relevant_posts(self, queries: List[str] = None, limit_per_query: int = 10) -> List[Dict[str, Any]]:
        """Return mock posts"""
        return [
            {
                "platform": "reddit",
                "platform_id": "abc123",
                "username": "user1",
                "source_url": "https://reddit.com/r/test/comments/abc123/test_post",
                "title": "Looking for solution",
                "body": "Need help with automation tool",
                "subreddit": "test",
                "created_utc": 1234567890
            },
            {
                "platform": "reddit",
                "platform_id": "def456",
                "username": "dev_user",
                "source_url": "https://reddit.com/r/dev/comments/def456/need_script",
                "title": "Need script to automate",
                "body": "Looking for tool to automate repetitive tasks",
                "subreddit": "dev",
                "created_utc": 1234567890
            }
        ]

    def is_configured(self) -> bool:
        return True
