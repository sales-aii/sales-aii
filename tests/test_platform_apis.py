# -*- coding: utf-8 -*-
"""
Reddit and GitHub integration tests.

All HTTP traffic is mocked; no network access and no API keys required.
Endpoints are asserted against the official API documentation:
- Reddit:  https://github.com/reddit-archive/reddit/wiki/OAuth2
- GitHub:  https://docs.github.com/en/rest/search/search
"""

import base64
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
# Reddit
# ==========================================================================
def _configure_reddit(monkeypatch, client_id="CID", secret="CSECRET"):
    monkeypatch.setattr("integrations.reddit.settings.REDDIT_CLIENT_ID", client_id)
    monkeypatch.setattr(
        "integrations.reddit.settings.REDDIT_CLIENT_SECRET", secret
    )


def test_reddit_requires_credentials(monkeypatch):
    from integrations.reddit import RedditIntegration

    _configure_reddit(monkeypatch, None, None)
    r = RedditIntegration()
    assert r.is_configured() is False
    with pytest.raises(APIError) as exc:
        r.search_posts("python help")
    assert "REDDIT_CLIENT_ID" in str(exc.value)


def test_reddit_oauth_flow_uses_client_credentials(monkeypatch):
    """Token request must follow the documented application-only OAuth flow"""
    from integrations.reddit import RedditIntegration

    token_calls = []

    def handler(request: httpx.Request):
        token_calls.append(request)
        if str(request.url) == RedditIntegration.TOKEN_URL:
            return httpx.Response(
                200, json={"access_token": "TOK", "token_type": "bearer",
                           "expires_in": 3600}
            )
        return httpx.Response(
            200,
            json={
                "kind": "Listing",
                "data": {"children": [{"kind": "t3", "data": {"id": "abc",
                                                              "title": "help"}}]},
            },
        )

    _patch_client(monkeypatch, handler)
    _configure_reddit(monkeypatch)

    r = RedditIntegration()
    posts = r.search_posts("python help")

    assert len(posts) == 1 and posts[0]["id"] == "abc"

    token_req = token_calls[0]
    assert str(token_req.url) == "https://www.reddit.com/api/v1/access_token"
    expected_basic = base64.b64encode(b"CID:CSECRET").decode()
    assert token_req.headers["Authorization"] == f"Basic {expected_basic}"
    assert token_req.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert b"grant_type=client_credentials" in token_req.content

    search_req = token_calls[1]
    assert str(search_req.url).startswith("https://oauth.reddit.com/search")
    assert search_req.headers["Authorization"] == "bearer TOK"
    assert "q=python+help" in str(search_req.url)


def test_reddit_token_is_cached(monkeypatch):
    from integrations.reddit import RedditIntegration

    token_hits = []

    def handler(request: httpx.Request):
        if str(request.url) == RedditIntegration.TOKEN_URL:
            token_hits.append(1)
            return httpx.Response(
                200, json={"access_token": "TOK", "expires_in": 3600}
            )
        return httpx.Response(200, json={"data": {"children": []}})

    _patch_client(monkeypatch, handler)
    _configure_reddit(monkeypatch)

    r = RedditIntegration()
    r.search_posts("a")
    r.search_posts("b")
    assert len(token_hits) == 1


def test_reddit_subreddit_search_uses_restrict_sr(monkeypatch):
    from integrations.reddit import RedditIntegration

    urls = []

    def handler(request: httpx.Request):
        if str(request.url) == RedditIntegration.TOKEN_URL:
            return httpx.Response(200, json={"access_token": "TOK",
                                            "expires_in": 3600})
        urls.append(str(request.url))
        return httpx.Response(200, json={"data": {"children": []}})

    _patch_client(monkeypatch, handler)
    _configure_reddit(monkeypatch)

    RedditIntegration().search_posts("help", subreddit="python", limit=5)
    assert urls[0].startswith("https://oauth.reddit.com/r/python/search")
    assert "restrict_sr=1" in urls[0]
    assert "limit=5" in urls[0]


def test_reddit_rejects_empty_query(monkeypatch):
    from integrations.reddit import RedditIntegration

    _configure_reddit(monkeypatch)
    with pytest.raises(APIError):
        RedditIntegration().search_posts("  ")


def test_reddit_http_error_raises(monkeypatch):
    """Reddit must never silently return [] on failure"""
    from integrations.reddit import RedditIntegration

    def handler(request: httpx.Request):
        if str(request.url) == RedditIntegration.TOKEN_URL:
            return httpx.Response(200, json={"access_token": "TOK",
                                            "expires_in": 3600})
        return httpx.Response(429, json={"message": "Too Many Requests"})

    _patch_client(monkeypatch, handler)
    _configure_reddit(monkeypatch)

    with pytest.raises(APIError) as exc:
        RedditIntegration().search_posts("x")
    assert "429" in str(exc.value)


def test_reddit_token_failure_raises(monkeypatch):
    from integrations.reddit import RedditIntegration

    def handler(request: httpx.Request):
        return httpx.Response(401, json={"message": "Unauthorized"})

    _patch_client(monkeypatch, handler)
    _configure_reddit(monkeypatch)

    with pytest.raises(APIError) as exc:
        RedditIntegration().search_posts("x")
    assert "401" in str(exc.value)


def test_reddit_comments_parses_second_listing(monkeypatch):
    from integrations.reddit import RedditIntegration

    def handler(request: httpx.Request):
        if str(request.url) == RedditIntegration.TOKEN_URL:
            return httpx.Response(200, json={"access_token": "TOK",
                                            "expires_in": 3600})
        return httpx.Response(
            200,
            json=[
                {"data": {"children": []}},
                {"data": {"children": [{"data": {"id": "c1",
                                                 "body": "hi"}}]}},
            ],
        )

    _patch_client(monkeypatch, handler)
    _configure_reddit(monkeypatch)

    comments = RedditIntegration().get_comments("t3_abc")
    assert len(comments) == 1 and comments[0]["body"] == "hi"


def test_reddit_search_relevant_deduplicates(monkeypatch):
    from integrations.reddit import RedditIntegration

    def handler(request: httpx.Request):
        if str(request.url) == RedditIntegration.TOKEN_URL:
            return httpx.Response(200, json={"access_token": "TOK",
                                            "expires_in": 3600})
        return httpx.Response(
            200,
            json={"data": {"children": [
                {"data": {"id": "same", "title": "t"}},
                {"data": {"id": "same", "title": "t"}},
            ]}},
        )

    _patch_client(monkeypatch, handler)
    _configure_reddit(monkeypatch)

    results = RedditIntegration().search_relevant_posts(["a", "b"])
    assert len(results) == 1


# ==========================================================================
# GitHub
# ==========================================================================
def _configure_github(monkeypatch, token="GHP_TOKEN"):
    monkeypatch.setattr("integrations.github.settings.GITHUB_TOKEN", token)


def test_github_requires_token(monkeypatch):
    from integrations.github import GitHubIntegration

    _configure_github(monkeypatch, None)
    g = GitHubIntegration()
    assert g.is_configured() is False
    with pytest.raises(APIError) as exc:
        g.search_issues("anything")
    assert "GITHUB_TOKEN" in str(exc.value)


def test_github_search_uses_official_endpoint_and_headers(monkeypatch):
    from integrations.github import GitHubIntegration

    captured = {}

    def handler(request: httpx.Request):
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        return httpx.Response(
            200, json={"total_count": 1, "incomplete_results": False,
                       "items": [{"number": 7, "title": "please add"}]}
        )

    _patch_client(monkeypatch, handler)
    _configure_github(monkeypatch)

    items = GitHubIntegration().search_issues("feature", limit=3)

    assert len(items) == 1 and items[0]["number"] == 7
    assert captured["url"].startswith("https://api.github.com/search/issues?")
    assert "q=feature" in captured["url"]
    assert "per_page=3" in captured["url"]
    assert captured["headers"]["authorization"] == "Bearer GHP_TOKEN"
    assert captured["headers"]["accept"] == "application/vnd.github+json"
    assert "x-github-api-version" in captured["headers"]


def test_github_rejects_overlong_query(monkeypatch):
    """GitHub rejects queries longer than 256 characters"""
    from integrations.github import GitHubIntegration

    _configure_github(monkeypatch)
    with pytest.raises(APIError) as exc:
        GitHubIntegration().search_issues("x" * 300)
    assert "256" in str(exc.value)


def test_github_rejects_empty_query(monkeypatch):
    from integrations.github import GitHubIntegration

    _configure_github(monkeypatch)
    with pytest.raises(APIError):
        GitHubIntegration().search_issues("   ")


def test_github_clamps_per_page(monkeypatch):
    from integrations.github import GitHubIntegration

    urls = []

    def handler(request: httpx.Request):
        urls.append(str(request.url))
        return httpx.Response(200, json={"items": []})

    _patch_client(monkeypatch, handler)
    _configure_github(monkeypatch)

    GitHubIntegration().search_issues("a", limit=500)
    assert "per_page=100" in urls[0]


def test_github_401_raises(monkeypatch):
    from integrations.github import GitHubIntegration

    def handler(request: httpx.Request):
        return httpx.Response(401, json={"message": "Bad credentials"})

    _patch_client(monkeypatch, handler)
    _configure_github(monkeypatch)

    with pytest.raises(APIError) as exc:
        GitHubIntegration().search_issues("a")
    assert "401" in str(exc.value)
    assert "Bad credentials" in str(exc.value)


def test_github_get_issue_validates_input(monkeypatch):
    from integrations.github import GitHubIntegration

    _configure_github(monkeypatch)
    g = GitHubIntegration()
    with pytest.raises(APIError):
        g.get_issue("", "repo", 1)
    with pytest.raises(APIError):
        g.get_issue("owner", "repo", "not-a-number")


def test_github_get_issue_builds_url(monkeypatch):
    from integrations.github import GitHubIntegration

    urls = []

    def handler(request: httpx.Request):
        urls.append(str(request.url))
        return httpx.Response(200, json={"number": 3, "title": "bug"})

    _patch_client(monkeypatch, handler)
    _configure_github(monkeypatch)

    issue = GitHubIntegration().get_issue("octocat", "Hello-World", 3)
    assert issue["title"] == "bug"
    assert urls[0] == "https://api.github.com/repos/octocat/Hello-World/issues/3"


def test_github_feature_request_search_uses_issue_qualifier(monkeypatch):
    """Without is:issue GitHub returns 422 for user tokens"""
    from integrations.github import GitHubIntegration

    queries = []

    def handler(request: httpx.Request):
        queries.append(request.url.params.get("q"))
        return httpx.Response(200, json={"items": []})

    _patch_client(monkeypatch, handler)
    _configure_github(monkeypatch)

    GitHubIntegration().search_feature_requests("dark mode")
    assert len(queries) == 2
    assert all("is:issue" in q for q in queries)