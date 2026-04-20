#!/usr/bin/env python3
"""
Price guide refresh agent.

Checks every entry in price_guide.py against current eBay active listing prices
and uses Claude to generate a prioritised update report.

Run this weekly or monthly to keep market values accurate.

Usage:
    uv run python scripts/refresh_price_guide.py
    uv run python scripts/refresh_price_guide.py --threshold 0.10   # flag >10% drift
    uv run python scripts/refresh_price_guide.py --dry-run          # report only, no Claude summary
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

import anthropic
import httpx

import config
from price_guide import PRICE_GUIDE
from sources.ebay_api import BROWSE_BASE, get_app_token
from sources.ebay_market import _trimmed_median, _MIN_LISTINGS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("refresh_price_guide")

_MODEL = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# eBay lookup
# ---------------------------------------------------------------------------

def _lookup_prices(keys: list[str]) -> dict[str, dict]:
    """
    For each price guide key, search eBay and return current listing stats.
    Returns {key: {median, count, min, max}} — key omitted if < _MIN_LISTINGS.
    """
    results: dict[str, dict] = {}

    with httpx.Client(timeout=20) as client:
        try:
            token = get_app_token(client)
        except Exception as e:
            log.error(f"Could not get eBay token: {e}")
            return {}

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_GB",
        }

        for i, key in enumerate(keys, 1):
            if i % 20 == 0:
                log.info(f"Progress: {i}/{len(keys)} entries checked")
            try:
                resp = client.get(
                    f"{BROWSE_BASE}/item_summary/search",
                    headers=headers,
                    params={
                        "q": key,
                        "filter": "buyingOptions:{FIXED_PRICE}",
                        "category_ids": "267",
                        "limit": 50,
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

                if len(prices) >= _MIN_LISTINGS:
                    results[key] = {
                        "median": _trimmed_median(prices),
                        "count": len(prices),
                        "min": min(prices),
                        "max": max(prices),
                    }

            except httpx.HTTPError as e:
                log.warning(f"eBay lookup failed for {key!r}: {e}")

    return results


# ---------------------------------------------------------------------------
# Drift analysis
# ---------------------------------------------------------------------------

def _analyse_drift(
    ebay_data: dict[str, dict],
    threshold: float,
) -> tuple[list[dict], list[dict], list[str]]:
    """
    Compare eBay medians against current guide prices.

    Returns:
        stale   — entries where drift exceeds threshold, sorted by drift magnitude
        ok      — entries within threshold
        no_data — keys with insufficient eBay listings
    """
    stale, ok, no_data = [], [], []

    for key, entry in PRICE_GUIDE.items():
        if key not in ebay_data:
            no_data.append(key)
            continue

        ebay = ebay_data[key]
        ebay_median = ebay["median"]

        # Compare against hardback price (the primary value for most entries)
        if isinstance(entry, dict):
            guide_price = entry.get("hardback") or entry.get("paperback")
        else:
            guide_price = entry

        if guide_price is None or guide_price <= 0:
            continue

        drift = (ebay_median - guide_price) / guide_price

        record = {
            "key": key,
            "guide_price": guide_price,
            "ebay_median": ebay_median,
            "ebay_count": ebay["count"],
            "ebay_min": ebay["min"],
            "ebay_max": ebay["max"],
            "drift": drift,
        }

        if abs(drift) > threshold:
            stale.append(record)
        else:
            ok.append(record)

    stale.sort(key=lambda r: abs(r["drift"]), reverse=True)
    return stale, ok, no_data


# ---------------------------------------------------------------------------
# Claude summary
# ---------------------------------------------------------------------------

def _claude_summary(stale: list[dict], threshold: float) -> str:
    """Ask Claude to summarise the stale entries and suggest concrete actions."""
    if not stale:
        return "All checked entries are within the drift threshold — no updates needed."

    lines = [
        f"Key: {r['key']!r} | Guide: £{r['guide_price']:.0f} | "
        f"eBay median: £{r['ebay_median']:.0f} ({r['ebay_count']} listings) | "
        f"Drift: {r['drift']:+.0%}"
        for r in stale
    ]
    data = "\n".join(lines)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=(
            "You are an expert in the Black Library Warhammer 40,000 secondary market. "
            "You help maintain a price guide for resellers buying and selling hardback books."
        ),
        messages=[{"role": "user", "content": (
            f"The following price guide entries have drifted more than {threshold:.0%} "
            "from current eBay asking prices. For each:\n"
            "1. Note if the drift is expected (e.g. recent reprint lowering prices, "
            "or a book going out of print raising them)\n"
            "2. Recommend a new guide price rounded to the nearest £1\n"
            "3. Flag any entries where the eBay data might be misleading "
            "(e.g. too few listings, mixed hardback/paperback results)\n\n"
            "Be concise. Group by action: UPDATE, INVESTIGATE, LEAVE.\n\n"
            f"{data}"
        )}],
    )
    return msg.content[0].text


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh price guide from eBay data")
    parser.add_argument(
        "--threshold", type=float, default=0.15,
        help="Flag entries where eBay median differs by more than this fraction (default 0.15 = 15%%)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Skip Claude summary — just show the raw drift data"
    )
    args = parser.parse_args()

    keys = list(PRICE_GUIDE.keys())
    log.info(f"Checking {len(keys)} price guide entries against eBay active listings...")

    ebay_data = _lookup_prices(keys)
    log.info(f"eBay data retrieved for {len(ebay_data)}/{len(keys)} entries")

    stale, ok, no_data = _analyse_drift(ebay_data, args.threshold)

    # --- Report ---
    print(f"\n{'='*65}")
    print(f"  PRICE GUIDE REFRESH REPORT")
    print(f"  Drift threshold: {args.threshold:.0%}  |  "
          f"{len(keys)} entries checked")
    print(f"{'='*65}")

    if stale:
        print(f"\nSTALE — {len(stale)} entries drifted >{args.threshold:.0%} from guide:\n")
        for r in stale:
            direction = "▲" if r["drift"] > 0 else "▼"
            print(
                f"  {direction} {r['key']:<40}  "
                f"guide £{r['guide_price']:.0f}  →  "
                f"eBay £{r['ebay_median']:.0f}  "
                f"({r['drift']:+.0%}, {r['ebay_count']} listings)"
            )

    print(f"\nOK     — {len(ok)} entries within {args.threshold:.0%}")
    print(f"NO DATA— {len(no_data)} entries (fewer than {_MIN_LISTINGS} eBay listings)")

    if no_data:
        print(f"         {', '.join(no_data[:8])}"
              + ("…" if len(no_data) > 8 else ""))

    if not args.dry_run and stale:
        print(f"\n{'─'*65}")
        print("CLAUDE ANALYSIS")
        print(f"{'─'*65}\n")
        print(_claude_summary(stale, args.threshold))

    print(f"\n{'='*65}")


if __name__ == "__main__":
    main()
