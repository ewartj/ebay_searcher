"""eBay source — fetches active Buy It Now listings for configured search terms."""
import logging

import httpx

import config
from models import Listing
from sources.ebay_api import BROWSE_BASE, get_app_token

log = logging.getLogger(__name__)


def fetch_ebay_listings(
    search_terms: list[tuple[str, int]] | None = None,
    category: str = "warhammer",
) -> list[Listing]:
    """Search eBay UK for BIN listings matching all configured search terms."""
    terms = search_terms if search_terms is not None else config.SEARCH_TERMS
    listings: list[Listing] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=20) as client:
        token = get_app_token(client)
        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        }

        for term, limit in terms:
            try:
                resp = client.get(
                    f"{BROWSE_BASE}/item_summary/search",
                    headers=headers,
                    params={
                        "q": term,
                        "filter": "buyingOptions:{FIXED_PRICE}",
                        "limit": limit,
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
                    if price_info.get("currency") != "GBP":
                        continue

                    try:
                        price = float(price_info.get("value", 0))
                    except (ValueError, TypeError):
                        continue

                    if price <= 0:
                        continue

                    condition = item.get("condition")
                    if condition and condition not in config.ACCEPTED_EBAY_CONDITIONS:
                        log.debug(f"eBay: skipping '{item.get('title', '')}' — condition '{condition}'")
                        continue

                    listings.append(
                        Listing(
                            title=item.get("title", ""),
                            price_gbp=price,
                            url=item.get("itemWebUrl", ""),
                            source="ebay",
                            condition=item.get("condition"),
                            image_url=item.get("image", {}).get("imageUrl"),
                            category=category,
                        )
                    )

                log.debug(
                    f"eBay '{term}' (limit {limit}): "
                    f"{len(data.get('itemSummaries', []))} items"
                )

            except httpx.HTTPError as e:
                log.warning(f"eBay search failed for '{term}': {e}")

    return listings
