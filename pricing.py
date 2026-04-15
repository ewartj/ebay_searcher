"""
Bargain detection pipeline.

Priority order for establishing market value:
  1. PRICE_GUIDE — your own known values (fastest, most accurate for key titles)
  2. eBay sold prices — live median from recent BIN sales (fallback for unlisted titles)
  3. Gemini estimate — AI fallback for titles with no sold history
"""
import logging
import statistics

import httpx

import config
from models import Bargain, Listing
from sources.ebay import fetch_sold_prices

log = logging.getLogger(__name__)

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/gemini-2.0-flash:generateContent"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lookup_price_guide(title: str) -> float | None:
    """Return the highest matching price from PRICE_GUIDE, or None."""
    title_lower = title.lower()
    matches = [
        price
        for keyword, price in config.PRICE_GUIDE.items()
        if keyword in title_lower
    ]
    return max(matches) if matches else None


def _median_sold_price(title: str) -> float | None:
    """Fetch recent eBay sold prices and return the median, or None."""
    prices = fetch_sold_prices(title)
    if not prices:
        return None
    median = statistics.median(prices)
    log.debug(f"eBay sold median for '{title}': £{median:.2f} ({len(prices)} sales)")
    return median


def _gemini_estimate(title: str) -> float | None:
    """
    Ask Gemini to estimate a fair UK resale value for a Black Library title.
    Used only when the price guide and eBay sold data both come up empty.
    """
    prompt = (
        "You are an expert in Black Library Warhammer 40,000 and Horus Heresy books "
        "and their UK secondary market resale values (eBay, Vinted). "
        "Reply with ONLY a GBP number (e.g. 35) for the fair Buy It Now market value of: "
        f"{title}. "
        "Reply with the single word UNKNOWN if you genuinely cannot estimate."
    )
    try:
        resp = httpx.post(
            _GEMINI_URL,
            params={"key": config.GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.upper() == "UNKNOWN":
            return None
        value = float(raw.replace("£", "").replace(",", "").split()[0])
        log.debug(f"Gemini estimate for '{title}': £{value:.2f}")
        return value
    except Exception as e:
        log.warning(f"Gemini estimate failed for '{title}': {e}")
        return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_market_price(listing: Listing) -> tuple[float, str] | tuple[None, None]:
    """
    Return (market_price_gbp, source_label) for a listing, or (None, None)
    if market value cannot be determined.
    """
    # 1 — price guide
    guide_price = _lookup_price_guide(listing.title)
    if guide_price:
        return guide_price, "price_guide"

    # 2 — eBay sold prices
    sold_price = _median_sold_price(listing.title)
    if sold_price:
        return sold_price, "ebay_sold"

    # 3 — Gemini estimate
    gemini_price = _gemini_estimate(listing.title)
    if gemini_price:
        return gemini_price, "gemini_estimate"

    return None, None


def find_bargains(listings: list[Listing]) -> list[Bargain]:
    """
    Filter listings to those at or below BARGAIN_THRESHOLD of market value.
    Sorted by discount percentage (best deals first).
    """
    bargains: list[Bargain] = []

    for listing in listings:
        market_price, source = get_market_price(listing)

        if market_price is None:
            log.debug(f"No market price for: {listing.title!r} — skipping")
            continue

        if market_price <= 0:
            continue

        ratio = listing.price_gbp / market_price
        if ratio <= config.BARGAIN_THRESHOLD:
            discount_pct = 1.0 - ratio
            bargains.append(
                Bargain(
                    listing=listing,
                    market_price=market_price,
                    discount_pct=discount_pct,
                    price_source=source,
                )
            )
            log.info(
                f"Bargain [{source}]: {listing.title!r} "
                f"£{listing.price_gbp:.2f} vs £{market_price:.2f} market "
                f"({discount_pct:.0%} off)"
            )

    # Best deals first
    bargains.sort(key=lambda b: b.discount_pct, reverse=True)
    return bargains
