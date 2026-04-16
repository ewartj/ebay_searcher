"""
Bargain detection pipeline.

Priority order for establishing market value:
  1. PRICE_GUIDE — your own known values (instant, no API call)
  2. Gemini FILTER — discard paperbacks/noise, keep collectible BL hardbacks only
  3. Gemini PRICE  — estimate value for the filtered shortlist (single batch)
"""
import json
import logging

import anthropic

import config
from models import Bargain, Listing

log = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
_MODEL = "claude-haiku-4-5-20251001"


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


def _parse_json_response(raw: str) -> dict | list:
    """Strip markdown fences and parse JSON from a Claude response."""
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _claude_filter(titles: list[str]) -> list[str]:
    """
    Ask Claude which titles are collectible Black Library hardbacks worth pricing.
    Returns index numbers so the response stays tiny regardless of title length.
    """
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))
    try:
        msg = _client.messages.create(
            model=_MODEL,
            max_tokens=512,
            system=(
                "You are an expert in Black Library Warhammer 40,000 and Horus Heresy "
                "collectible books and their UK secondary market."
            ),
            messages=[{"role": "user", "content": (
                "From the numbered list below, identify titles that are BLACK LIBRARY HARDBACKS "
                "likely to have meaningful secondary market resale value (limited editions, "
                "numbered copies, special editions, signed copies, or standard hardbacks "
                "of popular series).\n"
                "EXCLUDE: paperbacks, ebooks, audio, art books, codexes, rulebooks, "
                "army/painting guides, starter sets, or anything that is not Black Library "
                "prose fiction in hardback format.\n"
                "Reply with ONLY a JSON array of the LINE NUMBERS (integers) that pass. "
                "Example: [1, 4, 7]. Empty array if none qualify. No markdown, no explanation.\n\n"
                f"{numbered}"
            )}],
        )
        indices = _parse_json_response(msg.content[0].text)
        if isinstance(indices, list):
            kept = [titles[i - 1] for i in indices if isinstance(i, int) and 1 <= i <= len(titles)]
            log.info(f"Claude filter: {len(kept)}/{len(titles)} titles are collectible BL hardbacks")
            return kept
    except Exception as e:
        log.warning(f"Claude filter failed ({e}) — falling back to pricing all titles")
    return titles


def _claude_price(titles: list[str]) -> dict[str, float]:
    """
    Ask Claude for fair UK resale prices for a shortlist of collectible BL titles.
    Returns title -> GBP price for titles Claude can estimate.
    """
    if not titles:
        return {}

    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))
    try:
        msg = _client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            system=(
                "You are an expert in Black Library Warhammer 40,000 and Horus Heresy books "
                "and their UK secondary market resale values (eBay, Vinted)."
            ),
            messages=[{"role": "user", "content": (
                "For each title below give a fair GBP Buy It Now resale value.\n"
                "Reply with ONLY a valid JSON object mapping each title string exactly as given "
                "to a number (GBP price) or null if you cannot estimate. "
                "No markdown, no explanation.\n\n"
                f"{numbered}"
            )}],
        )
        estimates = _parse_json_response(msg.content[0].text)
        result = {}
        for title, value in estimates.items():
            if value is not None:
                try:
                    result[title] = float(value)
                except (ValueError, TypeError):
                    pass
        log.info(f"Claude priced {len(result)}/{len(titles)} titles")
        return result
    except Exception as e:
        log.warning(f"Claude pricing failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def find_bargains(listings: list[Listing]) -> list[Bargain]:
    """
    Filter listings to those at or below BARGAIN_THRESHOLD of market value.
    Sorted by discount percentage (best deals first).
    """
    # Pass 1: price guide (no API call)
    priced: dict[int, tuple[float, str]] = {}
    needs_gemini: list[tuple[int, str]] = []

    for i, listing in enumerate(listings):
        guide_price = _lookup_price_guide(listing.title)
        if guide_price:
            priced[i] = (guide_price, "price_guide")
        else:
            needs_gemini.append((i, listing.title))

    # Pass 2: Gemini filter → then price only what passes
    if needs_gemini:
        unknown_titles = [title for _, title in needs_gemini]
        log.info(f"{len(unknown_titles)} titles not in price guide — sending to Claude filter")

        collectible = _claude_filter(unknown_titles)

        if collectible:
            claude_prices = _claude_price(collectible)
            collectible_set = set(collectible)
            for i, title in needs_gemini:
                if title in collectible_set and title in claude_prices:
                    priced[i] = (claude_prices[title], "claude_estimate")

    # Pass 3: apply threshold
    bargains: list[Bargain] = []
    for i, listing in enumerate(listings):
        if i not in priced:
            log.debug(f"No market price for: {listing.title!r} — skipping")
            continue

        market_price, source = priced[i]
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

    bargains.sort(key=lambda b: b.discount_pct, reverse=True)
    return bargains
