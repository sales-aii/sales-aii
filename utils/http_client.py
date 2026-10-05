# -*- coding: utf-8 -*-
"""
Shared HTTP helper for outbound API calls.

Rules enforced here:
- every request has a timeout (no hanging calls)
- failures raise APIError instead of returning fake/empty results
- secrets are never logged; only method + host + status code
"""

from typing import Any, Dict, Optional

import httpx

from config.config import settings
from utils.exceptions import APIError


DEFAULT_TIMEOUT = 30


def request(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Any] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
    platform: str = "http",
    error_hints: Optional[Dict[int, str]] = None,
) -> httpx.Response:
    """
    Perform an HTTP request and raise APIError on any failure.

    Returns the raw httpx.Response on 2xx so callers can inspect status.

    error_hints maps a status code to a short actionable explanation appended
    to the raised error, so the UI can show something the user can act on
    instead of a bare status code.
    """
    timeout = timeout or DEFAULT_TIMEOUT
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json,
                data=data,
            )
    except httpx.TimeoutException as e:
        raise APIError(f"{platform}: request timed out after {timeout}s") from e
    except httpx.HTTPError as e:
        raise APIError(f"{platform}: connection error - {type(e).__name__}") from e

    if response.status_code >= 400:
        # Log status only - never headers/bodies which may carry secrets
        message = (
            f"{platform}: HTTP {response.status_code} for "
            f"{method} {_safe_host(url)}{_safe_error_detail(response)}"
        )
        hint = (error_hints or {}).get(response.status_code)
        if hint:
            message = f"{message} - {hint}"
        raise APIError(message)
    return response


def request_json(*args, **kwargs) -> Dict[str, Any]:
    """Perform a request and decode a JSON object body. Raises APIError otherwise."""
    payload = request_json_any(*args, **kwargs)
    if not isinstance(payload, dict):
        raise APIError(f"{kwargs.get('platform', 'http')}: unexpected JSON response type")
    return payload


def request_json_any(*args, **kwargs) -> Any:
    """
    Perform a request and decode the JSON body of any shape (object or array).

    Some documented endpoints (e.g. Reddit /comments/<id>) return a top-level
    JSON array, so callers that expect a list need this variant.
    """
    platform = kwargs.get("platform", "http")
    response = request(*args, **kwargs)
    try:
        return response.json()
    except ValueError as e:
        raise APIError(f"{platform}: response was not valid JSON") from e


def _safe_host(url: str) -> str:
    try:
        return httpx.URL(url).host
    except Exception:
        return "?"


def _safe_error_detail(response: httpx.Response) -> str:
    """
    Extract a short, secret-free error description.

    Only well-known error containers are read, and the value is truncated.
    """
    try:
        payload = response.json()
    except Exception:
        return ""
    if not isinstance(payload, dict):
        return ""

    message = None
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
    elif isinstance(error, str):
        message = error
    if not message:
        message = payload.get("message")
    if not message:
        message = payload.get("description")

    if not isinstance(message, str):
        return ""
    return f": {message[:200]}"


def default_headers() -> Dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": settings.REDDIT_USER_AGENT,
    }