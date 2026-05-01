"""
eBay sold-listing price fetcher using the Finding API.

Uses findCompletedItems to get *actual* sold prices — a stronger market signal
than active asking prices, since it reflects what buyers genuinely paid.

Auth: App ID only (no OAuth needed) via X-EBAY-SOA-SECURITY-APPNAME.

Notes on the Finding API:
- SoldItemsOnly is unreliable on EBAY-GB; we omit it and filter by sellingState
  in the response instead (EndedWithSales = actually sold).
- Full listing titles break the query — they're too long and contain characters
  like #, (), edition numbers that the API rejects with 500. Keywords are
  cleaned and truncated before sending.
"""
import json
import logging
import re
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

import config

log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

_FINDING_URL = "https://svcs.ebay.com/services/search/FindingService/v1"
_BOOKS_CATEGORY = "267"
_MIN_SALES = 3
_MAX_WORKERS = 5
_MAX_KEYWORD_LEN = 80


def fetch_sold_prices(titles: list[str]) -> dict[str, float]:
    """Returns {title: median_sold_gbp} for titles with sufficient sold-listing data."""
    return {t: s["median"] for t, s in fetch_sold_stats(titles).items()}


def fetch_sold_stats(titles: list[str]) -> dict[str, dict]:
    """
    Returns {title: {median, count, min, max}} from eBay UK completed/sold listings.
    Lookups run in parallel.
    """
    if not titles:
        return {}

    unique = list(dict.fromkeys(titles))

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(_lookup_sold, t): t for t in unique}
        for future in as_completed(futures):
            title, stats = future.result()
            if stats is not None:
                results[title] = stats

    log.info(f"eBay sold prices: {len(results)}/{len(unique)} titles with sale data")
    return results


def _clean_keywords(title: str) -> str:
    """
    Trim a full listing title down to a safe Finding API keyword string.

    The Finding API rejects long or special-character-heavy queries with 500.
    We strip problem characters, collapse whitespace, and truncate at a word
    boundary so the query stays meaningful.
    """
    cleaned = re.sub(r"[#()\[\]{}&+|'\"*:/]", " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= _MAX_KEYWORD_LEN:
        return cleaned
    truncated = cleaned[:_MAX_KEYWORD_LEN]
    last_space = truncated.rfind(" ")
    return truncated[:last_space] if last_space > 0 else truncated


def _lookup_sold(title: str, limit: int = 50) -> tuple[str, dict | None]:
    keywords = _clean_keywords(title)
    if not keywords:
        return title, None

    # Finding API: pass everything as query params (no SOA headers needed).
    # SoldItemsOnly is unreliable on EBAY-GB — filter by sellingState in response.
    params = {
        "OPERATION-NAME": "findCompletedItems",
        "SERVICE-VERSION": "1.0.0",
        "SECURITY-APPNAME": config.EBAY_CLIENT_ID,
        "RESPONSE-DATA-FORMAT": "JSON",
        "GLOBAL-ID": "EBAY-GB",
        "keywords": keywords,
        "categoryId": _BOOKS_CATEGORY,
        "itemFilter(0).name": "ListingType",
        "itemFilter(0).value": "FixedPrice",
        "paginationInput.entriesPerPage": str(limit),
        "outputSelector(0)": "SellingStatus",
    }

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(_FINDING_URL, params=params)
            resp.raise_for_status()
            try:
                data = resp.json()
            except json.JSONDecodeError:
                log.warning(f"eBay sold: non-JSON response for {title!r}")
                return title, None

        items = (
            data
            .get("findCompletedItemsResponse", [{}])[0]
            .get("searchResult", [{}])[0]
            .get("item", [])
        )

        prices = []
        for item in items:
            selling = item.get("sellingStatus", [{}])[0]
            state = selling.get("sellingState", [{}])[0].get("__value__", "")
            if state != "EndedWithSales":
                continue
            price_info = selling.get("currentPrice", [{}])[0]
            if price_info.get("@currencyId") != "GBP":
                continue
            try:
                prices.append(float(price_info["__value__"]))
            except (KeyError, ValueError, TypeError):
                continue

        if len(prices) < _MIN_SALES:
            log.debug(f"eBay sold: only {len(prices)} sale(s) for {title!r} — skipping")
            return title, None

        median = _trimmed_median(prices)
        log.debug(f"eBay sold: {title!r} → £{median:.2f} ({len(prices)} sales)")
        return title, {"median": median, "count": len(prices), "min": min(prices), "max": max(prices)}

    except httpx.HTTPStatusError as e:
        log.warning(f"eBay sold: HTTP {e.response.status_code} for {title!r} (keywords: {keywords!r})")
        return title, None
    except httpx.HTTPError as e:
        log.warning(f"eBay sold: connection error for {title!r} — {e}")
        return title, None


def _trimmed_median(prices: list[float]) -> float:
    prices = sorted(prices)
    n = len(prices)
    trim = max(1, n // 10)
    trimmed = prices[trim: n - trim] if n > 2 * trim else prices
    return statistics.median(trimmed)
