"""Depop source — searches Depop UK for subscription box fantasy hardbacks.

Depop has no official public API. This module calls their internal web API
endpoint. Usage is low-frequency (once a day) and for personal, non-commercial
use. The source skips silently on auth failures — set DEPOP_SESSION_TOKEN in
.env to authenticate if anonymous access stops working.
"""
import logging

import httpx

import config
from models import Listing

log = logging.getLogger(__name__)

_BASE = "https://www.depop.com"
_API_BASE = "https://webapi.depop.com"
_SEARCH_URL = f"{_API_BASE}/api/v2/search/products/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-GB,en;q=0.9",
    "Origin": _BASE,
    "Referer": _BASE + "/",
}


def _parse_price(price: object) -> float | None:
    if not isinstance(price, dict):
        return None
    if price.get("currencyCode", "GBP") != "GBP":
        return None
    try:
        value = float(price.get("priceAmount", 0))
        return value if value > 0 else None
    except (ValueError, TypeError):
        return None


def fetch_depop_listings(
    search_terms: list[tuple[str, int]] | None = None,
    category: str = "fantasy",
) -> list[Listing]:
    """Fetch fixed-price book listings from Depop UK."""
    terms = search_terms if search_terms is not None else config.DEPOP_FANTASY_SEARCH_TERMS
    listings: list[Listing] = []
    seen_ids: set[str] = set()

    headers = dict(_HEADERS)
    if config.DEPOP_SESSION_TOKEN:
        headers["Authorization"] = f"Bearer {config.DEPOP_SESSION_TOKEN}"

    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for term, limit in terms:
            try:
                resp = client.get(
                    _SEARCH_URL,
                    headers=headers,
                    params={
                        "q": term,
                        "itemsPerPage": limit,
                        "country": "gb",
                        "currency": "GBP",
                        "language": "en",
                    },
                )

                if resp.status_code in (401, 403):
                    log.warning(
                        "Depop: authentication required. "
                        "Set DEPOP_SESSION_TOKEN in .env (inspect browser network "
                        "requests on depop.com to find your Bearer token)."
                    )
                    return listings

                resp.raise_for_status()
                data = resp.json()

                log.debug(f"Depop '{term}' response keys: {list(data.keys())}")
                products = data.get("products", [])
                log.debug(f"Depop '{term}': {len(products)} products")

                for item in products:
                    item_id = str(item.get("id", ""))
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    price = _parse_price(item.get("price"))
                    if price is None:
                        continue

                    condition = item.get("condition") or item.get("status")
                    if condition and condition not in config.ACCEPTED_DEPOP_CONDITIONS:
                        log.debug(
                            f"Depop: skipping {item.get('description', '')!r} "
                            f"— condition '{condition}'"
                        )
                        continue

                    slug = item.get("slug", "")
                    url = f"{_BASE}/products/{slug}/" if slug else f"{_BASE}/products/{item_id}/"

                    previews = item.get("preview") or []
                    image_url = previews[0] if previews else None

                    title = (
                        item.get("title")
                        or item.get("description")
                        or item.get("name")
                        or ""
                    )

                    listings.append(
                        Listing(
                            title=title,
                            price_gbp=price,
                            url=url,
                            source="depop",
                            condition=condition,
                            image_url=image_url,
                            category=category,
                        )
                    )

            except httpx.HTTPStatusError as e:
                log.warning(f"Depop search failed for '{term}': HTTP {e.response.status_code}")
            except Exception as e:
                log.warning(f"Depop unexpected error for '{term}': {e}")

    return listings
