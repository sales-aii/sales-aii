# -*- coding: utf-8 -*-
"""
GitHub integration - official GitHub REST API.

Docs:    https://docs.github.com/en/rest/search/search
Base:    https://api.github.com
Auth:    Authorization: Bearer <token>
         Accept: application/vnd.github+json
         X-GitHub-Api-Version: <version>
"""

from typing import Any, Dict, List, Optional

from config.config import settings
from services.base_service import BaseService
from utils.exceptions import APIError
from utils.http_client import request_json

# GitHub rejects per_page values above 100
MAX_PER_PAGE = 100


class GitHubIntegration(BaseService):
    """
    GitHub API integration - uses official GitHub REST API v3
    """

    BASE_URL = "https://api.github.com"

    def __init__(self):
        super().__init__()
        self.platform = "github"
        self.token = settings.GITHUB_TOKEN

    def is_configured(self) -> bool:
        """Check if GitHub is configured"""
        return bool(self.token)

    def _require_token(self) -> str:
        if not self.token:
            raise APIError("GitHub: GITHUB_TOKEN is not set")
        return self.token

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._require_token()}",
            "X-GitHub-Api-Version": settings.GITHUB_API_VERSION,
        }

    @staticmethod
    def _validate_query(query: str) -> str:
        """GitHub rejects queries longer than 256 chars"""
        if not query or not query.strip():
            raise APIError("GitHub: search query cannot be empty")
        if len(query) > 256:
            raise APIError("GitHub: search query exceeds the 256 character limit")
        return query.strip()

    def _search(self, endpoint: str, query: str, limit: int,
                 sort: str = None, order: str = None) -> Dict[str, Any]:
        """Run a search endpoint and return the raw payload"""
        params: Dict[str, Any] = {
            "q": self._validate_query(query),
            "per_page": max(1, min(int(limit), MAX_PER_PAGE)),
        }
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order

        payload = request_json(
            "GET",
            f"{self.BASE_URL}{endpoint}",
            headers=self._headers(),
            params=params,
            platform=self.platform,
            timeout=settings.HTTP_TIMEOUT,
        )
        if payload.get("incomplete_results"):
            self.logger.warning(
                f"GitHub: '{query}' returned incomplete_results (search timeout)"
            )
        return payload

    def search_issues(self, query: str, limit: int = 25,
                       sort: str = "updated") -> List[Dict[str, Any]]:
        """Search issues - feature requests, bugs indicating need"""
        payload = self._search("/search/issues", query, limit, sort=sort)
        return payload.get("items", [])

    def search_repositories(self, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Search repositories"""
        payload = self._search("/search/repositories", query, limit)
        return payload.get("items", [])

    def get_issue(self, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
        """Get a specific issue"""
        if not owner or not repo:
            raise APIError("GitHub: owner and repo are required")
        try:
            number = int(issue_number)
        except (TypeError, ValueError) as e:
            raise APIError("GitHub: issue_number must be an integer") from e

        return request_json(
            "GET",
            f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{number}",
            headers=self._headers(),
            platform=self.platform,
            timeout=settings.HTTP_TIMEOUT,
        )

    def search_feature_requests(self, query: str, limit: int = 20,
                               queries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search specifically for feature requests / needs"""
        search_queries = queries or [
            f"{query} is:issue is:open label:enhancement",
            f"{query} is:issue is:open \"feature request\"",
        ]
        results: List[Dict[str, Any]] = []
        for q in search_queries[:2]:  # GitHub search rate limit: 30 req/min
            results.extend(self.search_issues(q, limit=limit))
        return results