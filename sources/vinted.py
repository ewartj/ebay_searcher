"""Vinted source — searches Vinted UK for Black Library books.

Vinted has no official public API. This module calls their internal catalog
endpoint. curl_cffi is used instead of httpx because Vinted's Cloudflare
protection checks TLS fingerprints — curl_cffi impersonates Chrome at that
level, which plain httpx/requests cannot do.
"""
import logging

from curl_cffi import requests as curl_requests

import config
from models import Listing

log = logging.getLogger(__name__)

_BASE = "https://www.vinted.co.uk"
_CATALOG_URL = f"{_BASE}/api/v2/catalog/items"

# curl_cffi sets browser-appropriate headers automatically when impersonating;
# we only override the fields Vinted specifically looks for.
_EXTRA_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": _BASE,
}


def _parse_price(raw: object) -> float | None:
    """
    Vinted returns price in two formats depending on API version:
      - plain string/float: "12.99"
      - object: {"amount": "12.99", "currency_code": "GBP"}
    Returns GBP float or None if unparseable / non-GBP.
    """
    if isinstance(raw, dict):
        if raw.get("currency_code", "GBP") != "GBP":
            return None
        raw = raw.get("amount", 0)
    try:
        value = float(raw)
        return value if value > 0 else None
    except (ValueError, TypeError):
        return None


def fetch_vinted_listings(
    search_terms: list[tuple[str, int]] | None = None,
    category: str = "warhammer",
) -> list[Listing]:
    """Fetch fixed-price book listings from Vinted UK."""
    terms = search_terms if search_terms is not None else config.VINTED_SEARCH_TERMS
    listings: list[Listing] = []
    seen_ids: set[str] = set()

    with curl_requests.Session() as session:
        # Step 1 — hit homepage to establish session cookies (Cloudflare handshake)
        try:
            session.get(_BASE, headers=_EXTRA_HEADERS, impersonate="chrome")
        except Exception as e:
            log.warning(f"Vinted: failed to get session — {e}")
            return []

        cookies = dict(session.cookies)
        if not cookies:
            log.warning("Vinted: no session cookies received — skipping")
            return []

        # Step 2 — attach CSRF token if present
        req_headers = dict(_EXTRA_HEADERS)
        csrf = cookies.get("XSRF-TOKEN") or cookies.get("csrf_token")
        if csrf:
            req_headers["X-CSRF-Token"] = csrf
        else:
            log.debug("Vinted: no CSRF token in cookies (read-only requests should still work)")

        # Step 3 — search each term
        for term, limit in terms:
            try:
                resp = session.get(
                    _CATALOG_URL,
                    headers=req_headers,
                    params={
                        "search_text": term,
                        "per_page": limit,
                        "order": "newest_first",
                    },
                    impersonate="chrome",
                )
                resp.raise_for_status()
                data = resp.json()

                log.debug(f"Vinted '{term}' response keys: {list(data.keys())}")

                items = data.get("items", [])
                log.debug(f"Vinted '{term}': {len(items)} items")

                if not items and "items" not in data:
                    log.warning(f"Vinted: unexpected response structure for '{term}': {list(data.keys())}")

                for item in items:
                    item_id = str(item.get("id", ""))
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    price = _parse_price(item.get("price"))
                    if price is None:
                        continue

                    condition = item.get("status")
                    if condition and condition not in config.ACCEPTED_VINTED_CONDITIONS:
                        log.debug(f"Vinted: skipping '{item.get('title', '')}' — condition '{condition}'")
                        continue

                    url = item.get("url") or f"/items/{item_id}"
                    if not url.startswith("http"):
                        url = _BASE + url

                    photos = item.get("photos") or []
                    photo = photos[0].get("url") if photos else None

                    listings.append(
                        Listing(
                            title=item.get("title", ""),
                            price_gbp=price,
                            url=url,
                            source="vinted",
                            condition=item.get("status"),
                            image_url=photo,
                            category=category,
                        )
                    )

            except Exception as e:
                log.warning(f"Vinted search failed for '{term}': {e}")

    return listings
