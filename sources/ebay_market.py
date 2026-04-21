"""
eBay active-listing market price estimator.

Searches eBay UK for active fixed-price GBP listings matching a title and
returns the trimmed median asking price as a market value estimate.

Why active listings rather than sold data
-----------------------------------------
eBay's Marketplace Insights API (actual sold prices) requires restricted
access not open to new developers. The Browse API only serves active listings.
A trimmed median of active asking prices is a reliable proxy — if 20 sellers
are listing Betrayer Hardback at £35–45, the market price is ~£40. The listing
at £12 is our bargain regardless of whether we have historical sold data.

Note: category_ids=267 is "Books, Comics & Magazines" on eBay UK.
"""
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from sources.ebay_api import BROWSE_BASE, get_app_token

log = logging.getLogger(__name__)

_BOOKS_CATEGORY = "267"   # eBay UK: Books, Comics & Magazines
_MIN_LISTINGS = 3         # Require at least this many prices to trust the median
_MAX_WORKERS = 5          # Parallel eBay requests — stay well within rate limits


def fetch_market_prices(titles: list[str]) -> dict[str, float]:
    """
    Returns {title: median_gbp} for titles with sufficient listing data.
    Convenience wrapper around fetch_market_stats.
    """
    return {t: s["median"] for t, s in fetch_market_stats(titles).items()}


def fetch_market_stats(titles: list[str]) -> dict[str, dict]:
    """
    Look up market prices for a list of titles using eBay active listings.
    Returns {title: {median, count, min, max}} for titles with sufficient data.
    Lookups run in parallel to avoid sequential latency for large shortlists.
    """
    if not titles:
        return {}

    unique = list(dict.fromkeys(titles))

    with httpx.Client(timeout=20) as bootstrap:
        try:
            token = get_app_token(bootstrap)
        except Exception as e:
            log.warning(f"eBay market price: could not get token — {e}")
            return {}

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
    }

    def lookup(title: str) -> tuple[str, dict | None]:
        with httpx.Client(timeout=20) as client:
            return title, _lookup_stats(client, headers, title)

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(lookup, t): t for t in unique}
        for future in as_completed(futures):
            title, stats = future.result()
            if stats is not None:
                results[title] = stats

    log.info(f"eBay market prices: {len(results)}/{len(unique)} titles priced")
    return results


def _lookup_stats(
    client: httpx.Client,
    headers: dict[str, str],
    title: str,
    limit: int = 50,
) -> dict | None:
    """
    Search eBay for a single title and return price stats.
    Returns {median, count, min, max} or None if fewer than _MIN_LISTINGS found.
    """
    try:
        resp = client.get(
            f"{BROWSE_BASE}/item_summary/search",
            headers=headers,
            params={
                "q": title,
                "filter": "buyingOptions:{FIXED_PRICE}",
                "category_ids": _BOOKS_CATEGORY,
                "limit": limit,
            },
        )
        resp.raise_for_status()
        items = resp.json().get("itemSummaries", [])

        prices = []
        for item in items:
            price_info = item.get("price", {})
            if price_info.get("currency") != "GBP":
                continue
            try:
                prices.append(float(price_info["value"]))
            except (KeyError, ValueError, TypeError):
                continue

        if len(prices) < _MIN_LISTINGS:
            log.debug(f"eBay: only {len(prices)} listing(s) for {title!r} — skipping")
            return None

        median = _trimmed_median(prices)
        log.debug(f"eBay: {title!r} → £{median:.2f} ({len(prices)} listings)")
        return {"median": median, "count": len(prices), "min": min(prices), "max": max(prices)}

    except httpx.HTTPStatusError as e:
        log.warning(f"eBay market price: HTTP {e.response.status_code} for {title!r}")
        return None
    except httpx.HTTPError as e:
        log.warning(f"eBay market price: connection error for {title!r} — {e}")
        return None


def _trimmed_median(prices: list[float]) -> float:
    """
    Median after removing the cheapest and most expensive 10%.
    Filters out data-entry errors (£0.99) and wildly optimistic prices (£999).
    """
    prices = sorted(prices)
    n = len(prices)
    trim = max(1, n // 10)
    trimmed = prices[trim : n - trim] if n > 2 * trim else prices
    return statistics.median(trimmed)
