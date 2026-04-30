"""Etsy source — searches Etsy for collectible book hardbacks.

Requires a free API key from https://www.etsy.com/developers.
Set ETSY_API_KEY in .env — the source skips silently if unset.
"""
import logging

import httpx

import config
from models import Listing

log = logging.getLogger(__name__)

_BASE = "https://openapi.etsy.com/v3/application"


def _gbp_price(price: dict) -> float | None:
    if price.get("currency_code") != "GBP":
        return None
    try:
        divisor_raw = price.get("divisor")
        divisor = int(divisor_raw) if divisor_raw is not None else 100
        if divisor == 0:
            return None
        value = int(price["amount"]) / divisor
        return value if value > 0 else None
    except (KeyError, ValueError, TypeError):
        return None


def fetch_etsy_listings(
    search_terms: list[tuple[str, int]] | None = None,
    category: str = "warhammer",
) -> list[Listing]:
    """Fetch active GBP listings from Etsy. Returns [] if ETSY_API_KEY is unset."""
    if not config.ETSY_API_KEY:
        log.debug("ETSY_API_KEY not configured — skipping Etsy source")
        return []

    terms = search_terms if search_terms is not None else config.ETSY_SEARCH_TERMS
    listings: list[Listing] = []
    seen_ids: set[str] = set()
    headers = {"x-api-key": config.ETSY_API_KEY}

    with httpx.Client(timeout=20) as client:
        for term, limit in terms:
            try:
                resp = client.get(
                    f"{_BASE}/listings/active",
                    headers=headers,
                    params={
                        "keywords": term,
                        "limit": min(limit, 100),
                        "sort_on": "score",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("results", []):
                    listing_id = str(item.get("listing_id", ""))
                    if not listing_id or listing_id in seen_ids:
                        continue
                    seen_ids.add(listing_id)

                    price = _gbp_price(item.get("price") or {})
                    if price is None:
                        continue

                    url = item.get("url") or f"https://www.etsy.com/listing/{listing_id}/"
                    images = item.get("images") or []
                    image_url = images[0].get("url_fullxfull") if images else None

                    listings.append(Listing(
                        title=item.get("title", ""),
                        price_gbp=price,
                        url=url,
                        source="etsy",
                        category=category,
                        image_url=image_url,
                    ))

            except httpx.HTTPStatusError as e:
                log.warning(f"Etsy '{term}': HTTP {e.response.status_code}")
            except Exception as e:
                log.warning(f"Etsy '{term}': {e}")

    return listings
