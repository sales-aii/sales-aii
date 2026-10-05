# -*- coding: utf-8 -*-
"""
Mock GitHub integration for testing
"""

from typing import List, Dict, Any


class MockGitHubIntegration:
    """Mock GitHub for unit tests"""

    def __init__(self):
        self.platform = "github"

    def search_feature_requests(self, query: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Return mock issues"""
        return [
            {
                "platform": "github",
                "platform_id": "12345",
                "username": "contributor",
                "source_url": "https://github.com/test/repo/issues/1",
                "title": "Feature: Add API integration",
                "body": "Need to integrate with external API",
                "repo": "test/repo",
                "issue_number": 1,
                "state": "open"
            },
            {
                "platform": "github",
                "platform_id": "12346",
                "username": "maintainer",
                "source_url": "https://github.com/test/repo2/issues/5",
                "title": "Need better export feature",
                "body": "Looking for export functionality",
                "repo": "test/repo2",
                "issue_number": 5,
                "state": "open"
            }
        ]

    def is_configured(self) -> bool:
        return True
