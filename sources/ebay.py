"""eBay source — fetches active Buy It Now listings and sold price history."""
import base64
import logging
import time
from typing import Any

import httpx

import config
from models import Listing

log = logging.getLogger(__name__)

_BROWSE_BASE = "https://api.ebay.com/buy/browse/v1"
_TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
_SCOPE = "https://api.ebay.com/oauth/api_scope"

# Cache the app token in-process (valid for 2 h; script runs in seconds)
_token_cache: dict[str, Any] = {}


def _get_app_token(client: httpx.Client) -> str:
    """Fetch (or return cached) OAuth application token."""
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


def fetch_ebay_listings() -> list[Listing]:
    """Search eBay UK for BIN listings matching all configured search terms."""
    listings: list[Listing] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=20) as client:
        token = _get_app_token(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        }

        for term in config.SEARCH_TERMS:
            try:
                resp = client.get(
                    f"{_BROWSE_BASE}/item_summary/search",
                    headers=headers,
                    params={
                        "q": term,
                        "filter": "buyingOptions:{FIXED_PRICE}",
                        "limit": 50,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("itemSummaries", []):
                    item_id = item.get("itemId", "")
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    price_info = item.get("price", {})
                    currency = price_info.get("currency", "")
                    if currency != "GBP":
                        continue

                    try:
                        price = float(price_info.get("value", 0))
                    except (ValueError, TypeError):
                        continue

                    if price <= 0:
                        continue

                    image = item.get("image", {}).get("imageUrl")
                    listings.append(
                        Listing(
                            title=item.get("title", ""),
                            price_gbp=price,
                            url=item.get("itemWebUrl", ""),
                            source="ebay",
                            condition=item.get("condition"),
                            image_url=image,
                        )
                    )

                log.debug(f"eBay '{term}': {len(data.get('itemSummaries', []))} items")

            except httpx.HTTPError as e:
                log.warning(f"eBay search failed for '{term}': {e}")

    return listings


