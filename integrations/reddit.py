# -*- coding: utf-8 -*-
"""
Reddit integration - official Reddit API with application-only OAuth.

Docs:  https://github.com/reddit-archive/reddit/wiki/OAuth2
Token: POST https://www.reddit.com/api/v1/access_token
       Basic auth (client_id : client_secret), grant_type=client_credentials
       -> {"access_token": "...", "token_type": "bearer", "expires_in": 3600}
API:   GET https://oauth.reddit.com/... with Authorization: bearer <token>

A "script" type app is the correct app type for a desktop tool
(https://www.reddit.com/prefs/apps).
"""

import time
from typing import Any, Dict, List, Optional

from config.config import settings
from services.base_service import BaseService
from utils.exceptions import APIError
from utils.http_client import request_json, request_json_any

# Reddit caps `limit` at 100
MAX_LIMIT = 100


class RedditIntegration(BaseService):
    """
    Reddit API integration - using official Reddit API
    """

    BASE_URL = "https://oauth.reddit.com"
    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"

    def __init__(self):
        super().__init__()
        self.platform = "reddit"
        self.client_id = settings.REDDIT_CLIENT_ID
        self.client_secret = settings.REDDIT_CLIENT_SECRET
        self.user_agent = settings.REDDIT_USER_AGENT
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        """Check if Reddit is configured"""
        return bool(self.client_id and self.client_secret)

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------
    def _require_credentials(self) -> None:
        if not self.client_id or not self.client_secret:
            raise APIError(
                "Reddit: REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET are not set"
            )

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Fetch (and cache) an application-only OAuth token.

        Reddit tokens expire after 1 hour, so refresh slightly early.
        """
        self._require_credentials()
        now = time.monotonic()
        if not force_refresh and self._access_token and now < self._token_expires_at:
            return self._access_token

        credentials = f"{self.client_id}:{self.client_secret}"
        payload = request_json(
            "POST",
            self.TOKEN_URL,
            headers={
                "Authorization": f"Basic {_basic(credentials)}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.user_agent,
            },
            data={"grant_type": "client_credentials"},
            platform=self.platform,
            timeout=settings.HTTP_TIMEOUT,
        )

        token = payload.get("access_token")
        if not token:
            raise APIError("Reddit: token response did not contain an access_token")

        expires_in = int(payload.get("expires_in") or 3600)
        # refresh 60s before the real expiry
        self._token_expires_at = now + max(60, expires_in - 60)
        self._access_token = token
        self.logger.info(
            f"Reddit OAuth token acquired (valid for {expires_in}s)"
        )
        return token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"bearer {self.get_access_token()}",
            "User-Agent": self.user_agent,
        }

    # ------------------------------------------------------------------
    # Read endpoints
    # ------------------------------------------------------------------
    def _get_listing(self, path: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        payload = request_json(
            "GET",
            f"{self.BASE_URL}{path}",
            headers=self._headers(),
            params=params,
            platform=self.platform,
            timeout=settings.HTTP_TIMEOUT,
        )
        data = payload.get("data") or {}
        children = data.get("children") or []
        return [child.get("data", {}) for child in children]

    def search_posts(self, query: str, subreddit: Optional[str] = None,
                     limit: int = 25, sort: str = "relevance",
                     time_filter: str = "all") -> List[Dict[str, Any]]:
        """Search posts. Returns [] only when Reddit genuinely has no matches."""
        if not query or not query.strip():
            raise APIError("Reddit: search query cannot be empty")

        params: Dict[str, Any] = {
            "q": query.strip(),
            "sort": sort,
            "t": time_filter,
            "limit": max(1, min(int(limit), MAX_LIMIT)),
            "raw_json": 1,
        }
        if subreddit:
            params["restrict_sr"] = 1
            path = f"/r/{subreddit}/search"
        else:
            path = "/search"

        posts = self._get_listing(path, params)
        self.logger.info(f"Reddit search '{query}' returned {len(posts)} posts")
        return posts

    def search_subreddits(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search subreddits"""
        if not query or not query.strip():
            raise APIError("Reddit: search query cannot be empty")
        params = {
            "q": query.strip(),
            "limit": max(1, min(int(limit), MAX_LIMIT)),
            "raw_json": 1,
        }
        return self._get_listing("/subreddits/search", params)

    def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get a specific post by fullname or id"""
        if not post_id:
            raise APIError("Reddit: post_id is required")
        name = post_id if post_id.startswith("t3_") else f"t3_{post_id}"
        payload = request_json(
            "GET",
            f"{self.BASE_URL}/api/info",
            headers=self._headers(),
            params={"id": name, "raw_json": 1},
            platform=self.platform,
            timeout=settings.HTTP_TIMEOUT,
        )
        children = payload.get("data") or []
        if not children:
            raise APIError(f"Reddit: post '{post_id}' not found")
        return children[0]

    def get_comments(self, post_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get the comments of a post.

        Reddit returns [postListing, commentListing] for /comments/<id>.
        """
        if not post_id:
            raise APIError("Reddit: post_id is required")
        bare_id = post_id[3:] if post_id.startswith("t3_") else post_id
        payload = request_json_any(
            "GET",
            f"{self.BASE_URL}/comments/{bare_id}",
            headers=self._headers(),
            params={"limit": max(1, min(int(limit), MAX_LIMIT)), "raw_json": 1},
            platform=self.platform,
            timeout=settings.HTTP_TIMEOUT,
        )
        if not isinstance(payload, list) or len(payload) < 2:
            raise APIError(f"Reddit: unexpected comments payload for '{post_id}'")
        children = (payload[1].get("data") or {}).get("children") or []
        return [child.get("data", {}) for child in children]

    def search_relevant_posts(self, queries: List[str],
                              limit_per_query: int = 15) -> List[Dict[str, Any]]:
        """Run several searches and merge the results, de-duplicated by post id."""
        seen: set = set()
        results: List[Dict[str, Any]] = []
        for query in queries:
            posts = self.search_posts(query, limit=limit_per_query)
            for post in posts:
                post_id = post.get("id")
                if post_id and post_id not in seen:
                    seen.add(post_id)
                    results.append(post)
        return results


def _basic(credentials: str) -> str:
    import base64
    return base64.b64encode(credentials.encode("utf-8")).decode("ascii")