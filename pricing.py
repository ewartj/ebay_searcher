"""
Bargain detection pipeline.

Priority order for establishing market value:
  1. PRICE_GUIDE   — your own known values (instant, no API call)
  2. Claude FILTER — discard paperbacks/noise, keep collectible BL hardbacks only
  3. eBay ACTIVE   — trimmed median of current eBay asking prices (real market data)
  4. Claude PRICE  — estimate value for anything eBay couldn't price

Bundles (multi-book lots) are detected separately and flagged for manual review.
"""
import json
import logging
import re

import anthropic

import config
from models import Bargain, Listing
from sources.ebay_market import fetch_market_prices

log = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
_MODEL = "claude-haiku-4-5-20251001"

_BUNDLE_RE = re.compile(
    r"\bbundle\b|\bjob lot\b|\blot of \d|\bx\d+\b|\bbooks \d[-–]\d",
    re.IGNORECASE,
)

_WARHAMMER_RE = re.compile(
    r"warhammer|black library|horus heresy|40[,.]?000|40k|"
    r"age of sigmar|warhammer fantasy|old world|necromunda|"
    r"blood bowl|adeptus|space marine|chaos marine|astartes",
    re.IGNORECASE,
)

_PAPERBACK_RE = re.compile(
    r"\bpaperback\b|\b\(pb\)\b|\bpb\b|\bsmall pb\b|\bpocket\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lookup_price_guide(title: str) -> float | None:
    """
    Return the best matching price from PRICE_GUIDE for this listing title.
    Detects whether the listing is a paperback and returns the appropriate price.
    Returns None if no match, or if the listing is a paperback and only a
    hardback price exists (so Claude can price it instead).
    """
    title_lower = title.lower()
    is_paperback = bool(_PAPERBACK_RE.search(title))

    best: float | None = None
    for keyword, entry in config.PRICE_GUIDE.items():
        if keyword not in title_lower:
            continue
        if isinstance(entry, dict):
            if is_paperback:
                price = entry.get("paperback")
            else:
                price = entry.get("hardback")
            if price is None:
                continue  # format not in guide — fall through to Claude
        else:
            if is_paperback:
                continue  # plain float = hardback only — fall through to Claude
            price = entry
        if best is None or price > best:
            best = price

    return best


def _parse_json_response(raw: str) -> dict | list:
    """
    Extract and parse JSON from a Claude response.
    Handles markdown fences and preamble/postamble text that Claude occasionally
    includes despite instructions to return only JSON.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Claude added text around the JSON — extract the first array or object
    for start, end in (("[", "]"), ("{", "}")):
        s = raw.find(start)
        e = raw.rfind(end)
        if s != -1 and e > s:
            try:
                return json.loads(raw[s : e + 1])
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("No valid JSON found in response", raw, 0)


def _claude_filter(titles: list[str], client: anthropic.Anthropic) -> list[str]:
    """
    Ask Claude which titles are collectible Black Library hardbacks worth pricing.
    Returns index numbers so the response stays tiny regardless of title length.
    """
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))
    try:
        msg = client.messages.create(
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


def _claude_price(titles: list[str], client: anthropic.Anthropic) -> dict[str, float]:
    """
    Ask Claude for fair UK resale prices for a shortlist of collectible BL titles.
    Returns title -> GBP price for titles Claude can estimate.
    """
    if not titles:
        return {}

    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(titles))
    try:
        msg = client.messages.create(
            model=_MODEL,
            max_tokens=4096,
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

def find_bargains(
    listings: list[Listing],
    *,
    claude_client: anthropic.Anthropic | None = None,
) -> tuple[list[Bargain], list[Listing]]:
    """
    Returns (bargains, bundles).

    bargains — listings at or below BARGAIN_THRESHOLD of market value, best first.
    bundles  — listings that look like multi-book lots, flagged for manual review.
    """
    client = claude_client if claude_client is not None else _client

    # Separate bundles upfront — don't try to auto-price them
    bundles: list[Listing] = []
    singles: list[tuple[int, Listing]] = []

    for i, listing in enumerate(listings):
        if _BUNDLE_RE.search(listing.title) and _WARHAMMER_RE.search(listing.title):
            listing.is_bundle = True
            bundles.append(listing)
            log.info(f"Bundle flagged for review: {listing.title!r} £{listing.price_gbp:.2f}")
        else:
            singles.append((i, listing))

    if bundles:
        log.info(f"{len(bundles)} bundle(s) flagged for manual review")

    # Pass 1: price guide (no API call) — skip obvious paperbacks
    priced: dict[int, tuple[float, str]] = {}
    needs_claude: list[tuple[int, str]] = []

    for i, listing in singles:
        guide_price = _lookup_price_guide(listing.title)
        if guide_price:
            priced[i] = (guide_price, "price_guide")
        else:
            needs_claude.append((i, listing.title))

    # Pass 2: Claude filter — keep only collectible BL hardbacks
    if needs_claude:
        unknown_titles = [title for _, title in needs_claude]
        log.info(f"{len(unknown_titles)} titles not in price guide — sending to Claude filter")

        collectible = _claude_filter(unknown_titles, client)
        collectible_set = set(collectible)

        if collectible:
            # Pass 3: eBay active listings median (real market data, no API restrictions)
            ebay_prices = fetch_market_prices(collectible)

            still_needs_claude: list[tuple[int, str]] = []
            for i, title in needs_claude:
                if title not in collectible_set:
                    continue
                if title in ebay_prices:
                    priced[i] = (ebay_prices[title], "ebay_active")
                else:
                    still_needs_claude.append((i, title))

            # Pass 4: Claude price for anything eBay couldn't price
            if still_needs_claude:
                remaining = [t for _, t in still_needs_claude]
                log.info(
                    f"{len(remaining)} titles not priced by eBay — sending to Claude"
                )
                claude_prices = _claude_price(remaining, client)
                for i, title in still_needs_claude:
                    if title in claude_prices:
                        priced[i] = (claude_prices[title], "claude_estimate")

    # Pass 3: apply threshold
    bargains: list[Bargain] = []
    for i, listing in singles:
        if i not in priced:
            log.debug(f"No market price for: {listing.title!r} — skipping")
            continue

        market_price, source = priced[i]
        if market_price <= 0:
            continue

        ratio = listing.price_gbp / market_price
        profit = market_price - listing.price_gbp
        if ratio <= config.BARGAIN_THRESHOLD and profit >= config.MIN_PROFIT:
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
    return bargains, bundles
