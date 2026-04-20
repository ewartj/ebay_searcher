#!/usr/bin/env python3
"""
Genre price tracker — records weekly eBay median prices for fantasy and
sci-fi authors/series to build trend data over time.

Run weekly (e.g. Sunday morning, before weekly_digest.py):
    uv run python scripts/genre_tracker.py

Suggested cron (Sunday 08:00):
    0 8 * * 0 cd /path/to/ebay_searcher && uv run python scripts/genre_tracker.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from db import init_db, record_genre_prices
from sources.ebay_market import fetch_market_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("genre_tracker")


def main() -> None:
    init_db()

    terms = [term for term, _ in config.GENRE_SEARCH_TERMS]
    label_map = dict(config.GENRE_SEARCH_TERMS)

    log.info(f"Genre tracker: checking {len(terms)} terms against eBay...")

    all_stats = fetch_market_stats(terms)

    snapshots = [
        (term, label_map[term], stats)
        for term, stats in all_stats.items()
    ]

    for term, label, stats in snapshots:
        log.info(
            f"  {label}: £{stats['median']:.2f} median "
            f"(£{stats['min']:.0f}–£{stats['max']:.0f}, {stats['count']} listings)"
        )

    skipped = len(terms) - len(snapshots)
    if skipped:
        log.info(f"  {skipped} term(s) skipped — fewer than 3 eBay listings found")

    if snapshots:
        record_genre_prices(snapshots)

    log.info(
        f"Genre tracker complete: {len(snapshots)}/{len(terms)} terms recorded"
    )


if __name__ == "__main__":
    main()
