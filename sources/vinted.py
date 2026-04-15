"""Vinted source — searches Vinted UK for Black Library books.

Vinted has no official public API.  This module calls their internal catalog
endpoint using a session cookie obtained from the homepage.  Usage is low-
frequency (once a day) and for personal, non-commercial price monitoring.
"""
import logging

import httpx

import config
from models import Listing

log = logging.getLogger(__name__)

_BASE = "https://www.vinted.co.uk"
_CATALOG_URL = f"{_BASE}/api/v2/catalog/items"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": _BASE,
}


def _get_session_cookies(client: httpx.Client) -> dict[str, str]:
    """
    Hit the Vinted homepage to acquire a valid session cookie.
    Vinted requires a real session for catalog API calls.
    """
    resp = client.get(_BASE, headers=_HEADERS, follow_redirects=True)
    # httpx stores cookies on the client automatically; return them explicitly
    # so callers can see we have a session.
    return dict(client.cookies)


def fetch_vinted_listings() -> list[Listing]:
    """Fetch Buy It Now (all Vinted listings are fixed-price) BL books."""
    listings: list[Listing] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        cookies = _get_session_cookies(client)
        if not cookies:
            log.warning("Vinted: failed to obtain session cookies — skipping")
            return []

        for term in config.SEARCH_TERMS:
            try:
                resp = client.get(
                    _CATALOG_URL,
                    headers=_HEADERS,
                    params={
                        "search_text": term,
                        "per_page": 96,
                        "order": "newest_first",
                        "currency": "GBP",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                items = data.get("items", [])
                log.debug(f"Vinted '{term}': {len(items)} items")

                for item in items:
                    item_id = str(item.get("id", ""))
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    # Price comes as a string like "12.99"
                    try:
                        price = float(item.get("price", 0))
                    except (ValueError, TypeError):
                        continue

                    if price <= 0:
                        continue

                    url = item.get("url") or f"{_BASE}/items/{item_id}"
                    if not url.startswith("http"):
                        url = _BASE + url

                    photo = None
                    photos = item.get("photos", [])
                    if photos:
                        photo = photos[0].get("url")

                    listings.append(
                        Listing(
                            title=item.get("title", ""),
                            price_gbp=price,
                            url=url,
                            source="vinted",
                            condition=item.get("status"),
                            image_url=photo,
                        )
                    )

            except httpx.HTTPError as e:
                log.warning(f"Vinted search failed for '{term}': {e}")
            except Exception as e:
                log.warning(f"Vinted unexpected error for '{term}': {e}")

    return listings
