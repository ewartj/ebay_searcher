"""
Shared eBay API utilities — OAuth token management and Browse API base URL.

Both ebay.py (active listings fetch) and ebay_market.py (market price lookup)
import from here so auth logic lives in one place.
"""
import base64
import logging
import time
from typing import Any

import httpx

import config

log = logging.getLogger(__name__)

BROWSE_BASE = "https://api.ebay.com/buy/browse/v1"
_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
_SCOPE = "https://api.ebay.com/oauth/api_scope"

_token_cache: dict[str, Any] = {}


def get_app_token(client: httpx.Client) -> str:
    """Return a valid OAuth application token, using the in-process cache."""
    now = time.time()
    if _token_cache.get("token") and now < _token_cache.get("expires_at", 0):
        return _token_cache["token"]

    credentials = base64.b64encode(
        f"{config.EBAY_CLIENT_ID}:{config.EBAY_CLIENT_SECRET}".encode()
    ).decode()

    resp = client.post(
        _TOKEN_URL,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials", "scope": _SCOPE},
    )
    resp.raise_for_status()
    data = resp.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = now + data["expires_in"] - 60
    return _token_cache["token"]
