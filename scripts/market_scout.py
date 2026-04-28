#!/usr/bin/env python3
"""
Market scout — weekly niche opportunity discovery.

Probes candidate search terms against eBay active listings, scores each by
price variance and liquidity (high variance = sellers don't know values =
arbitrage opportunity), asks Claude to identify the most promising niches,
and sends a digest to Telegram.

Run weekly (e.g. after genre_tracker.py):
    uv run python scripts/market_scout.py
    uv run python scripts/market_scout.py --dry-run
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

import config
from notifier import send_digest_alert
from sources.ebay_market import fetch_market_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("market_scout")

_MODEL = "claude-haiku-4-5-20251001"
_TOP_N = 12


def _opportunity_score(stats: dict) -> float:
    """
    Score = price spread * liquidity cap.

    Price spread: (max - min) / median — how inconsistently sellers price this niche.
    High spread means some sellers are underpricing, which is where profit lives.

    Liquidity: capped at 1.0 above 20 listings — enough buyers to sell into.
    """
    median = stats.get("median", 0)
    high = stats.get("max", 0)
    low = stats.get("min", 0)
    count = stats.get("count", 0)
    if median <= 0 or high < low:
        return 0.0
    spread = (high - low) / median
    liquidity = min(1.0, count / 20)
    return spread * liquidity


def _build_prompt(candidates: list[dict]) -> str:
    lines = [
        "You are an expert in the UK secondhand collectible book market.",
        "A reseller currently focuses on Black Library / Warhammer hardbacks but wants to expand.",
        "Below are candidate niches with their eBay active listing stats.",
        "",
        "opportunity_score = price_spread × liquidity. Higher = more inconsistent pricing",
        "with real buyer demand = better arbitrage conditions.",
        "",
        "Write a concise scout report (max 18 lines, plain text). Format each niche as one of:",
        "  STRONG: [niche] — one sentence why it's a great opportunity",
        "  MODERATE: [niche] — one sentence on the opportunity and caveat",
        "  SKIP: [niche] — one sentence why it's not worth pursuing",
        "End with: RECOMMENDATION: one specific actionable step for this week.",
        "",
        "NICHE DATA:",
    ]
    for c in candidates:
        s = c["stats"]
        lines.append(
            f"  {c['label']}: median £{s['median']:.0f}, "
            f"range £{s['min']:.0f}–£{s['max']:.0f}, "
            f"{s['count']} listings, score {c['score']:.2f}"
        )
    return "\n".join(lines)


def run_market_scout(dry_run: bool = False) -> int:
    """Run the niche scout and send (or print) the report. Returns 0 on success."""
    terms = config.NICHE_SCOUT_TERMS
    if not terms:
        log.info("No NICHE_SCOUT_TERMS configured — skipping market scout")
        return 0

    log.info(f"Market scout: probing {len(terms)} candidate niches on eBay...")
    search_terms = [term for term, _ in terms]
    label_map = dict(terms)

    all_stats = fetch_market_stats(search_terms)
    if not all_stats:
        log.warning("Market scout: no eBay data returned — skipping this week")
        return 0

    candidates = sorted(
        [
            {
                "term": term,
                "label": label_map.get(term, term),
                "stats": stats,
                "score": _opportunity_score(stats),
            }
            for term, stats in all_stats.items()
        ],
        key=lambda x: x["score"],
        reverse=True,
    )

    top = candidates[:_TOP_N]
    log.info(
        f"Market scout: {len(candidates)}/{len(terms)} niches with data — "
        f"sending top {len(top)} to Claude"
    )

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=_MODEL,
        max_tokens=700,
        messages=[{"role": "user", "content": _build_prompt(top)}],
    )
    first = msg.content[0] if msg.content else None
    report = (
        first.text.strip()
        if isinstance(first, anthropic.types.TextBlock)
        else "(No report generated)"
    )

    skipped = len(terms) - len(all_stats)
    footer = f"({len(candidates)} niches scored"
    if skipped:
        footer += f", {skipped} skipped — too few eBay listings"
    footer += ")"

    message = f"Warhammer Scout — Weekly Niche Scout\n\n{report}\n\n{footer}"

    if dry_run:
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60)
        log.info("Dry run — report printed, not sent to Telegram")
    else:
        send_digest_alert(message)
        log.info("Market scout report sent to Telegram")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Weekly niche opportunity scout")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report to console instead of sending to Telegram",
    )
    args = parser.parse_args()
    sys.exit(run_market_scout(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
