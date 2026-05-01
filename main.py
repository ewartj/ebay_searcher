#!/usr/bin/env python3
"""
Warhammer Scout — daily eBay + Vinted bargain finder for Black Library books.

Run manually:   python main.py
Run dry-run:    python main.py --dry-run
Run daily:      cron / systemd timer, or AWS Lambda (see deploy/)
"""
import argparse
import logging
import logging.handlers
import sys
from pathlib import Path

import config
from db import (
    filter_new_alerts,
    get_feedback_examples,
    get_previously_alerted_urls,
    get_recent_source_counts,
    init_db,
    record_alerted_urls,
    record_scan,
    record_source_counts,
    store_alert_positions,
)
from notifier import (
    format_bargains,
    format_bundles,
    format_fantasy_bargains,
    format_fantasy_bundles,
    poll_feedback,
    send_bargain_alert,
    send_fantasy_alert,
)
from pricing import find_bargains
from sources import SOURCES
from sources.buyback import enrich_bargains
from sources.ebay import fetch_ebay_listings
from sources.etsy import fetch_etsy_listings
from sources.vinted import fetch_vinted_listings

_LOG_FILE = Path(__file__).parent / "data" / "warhammer_scout.log"


def _mark_multi_source(listings: list, bargains: list) -> None:
    """Flag bargains whose ISBN appears in listings from 2+ distinct sources."""
    isbn_sources: dict[str, set[str]] = {}
    isbn_urls: dict[str, list[str]] = {}
    for listing in listings:
        if listing.isbn:
            isbn_sources.setdefault(listing.isbn, set()).add(listing.source)
            isbn_urls.setdefault(listing.isbn, []).append(listing.url)

    multi_urls = {
        url
        for isbn, srcs in isbn_sources.items()
        if len(srcs) >= 2
        for url in isbn_urls.get(isbn, [])
    }
    for bargain in bargains:
        if bargain.listing.url in multi_urls:
            bargain.multi_source = True


def setup_logging() -> None:
    """Configure logging. In Lambda, only a StreamHandler is added (CloudWatch
    captures stdout). Locally, a rotating file handler is also attached."""
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handlers: list[logging.Handler] = [logging.StreamHandler()]

    if not config.IS_LAMBDA:
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            _LOG_FILE, maxBytes=1_000_000, backupCount=7, encoding="utf-8"
        ))

    for h in handlers:
        h.setFormatter(fmt)

    logging.basicConfig(level=logging.INFO, handlers=handlers)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def run_scan(dry_run: bool = False) -> int:
    """
    Execute one full scan: fetch → price → notify → record.
    Returns 0 on success, 1 on error.
    Called by main() for CLI use and by lambda_handler for Lambda invocations.
    """
    log = logging.getLogger("warhammer_scout")

    if dry_run:
        log.info("=== Warhammer Scout scan starting (DRY RUN — no notifications) ===")
    else:
        try:
            config.validate()
        except ValueError as e:
            log.error(f"Configuration error: {e}")
            return 1
        log.info("=== Warhammer Scout scan starting ===")
        init_db()
        # Poll for feedback from previous alerts before anything else
        poll_feedback(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, bot="wh")
        if config.TELEGRAM_FANTASY_BOT_TOKEN:
            poll_feedback(config.TELEGRAM_FANTASY_BOT_TOKEN, config.TELEGRAM_FANTASY_CHAT_ID, bot="fa")

    listings = []
    source_listing_counts: dict[str, int] = {}

    # Fetch Warhammer listings via the standard SOURCES registry
    for source_name, fetch in SOURCES.items():
        try:
            fetched = fetch()
            log.info(f"{source_name}: {len(fetched)} listings fetched")
            listings.extend(fetched)
            source_listing_counts[source_name] = len(fetched)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            log.error(f"{source_name} source failed: {e}")
            source_listing_counts[source_name] = 0

    # Fetch Fantasy/Sci-fi listings (tagged category="fantasy")
    for source_name, fetch_fn, terms in [
        ("ebay_fantasy",   fetch_ebay_listings,    config.FANTASY_SEARCH_TERMS),
        ("vinted_fantasy", fetch_vinted_listings,  config.FANTASY_VINTED_SEARCH_TERMS),
        ("etsy_fantasy",   fetch_etsy_listings,    config.ETSY_FANTASY_SEARCH_TERMS),
    ]:
        try:
            fetched = fetch_fn(terms, "fantasy")
            log.info(f"{source_name}: {len(fetched)} listings fetched")
            listings.extend(fetched)
            source_listing_counts[source_name] = len(fetched)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            log.error(f"{source_name} source failed: {e}")
            source_listing_counts[source_name] = 0

    if not listings:
        log.warning("No listings retrieved from any source — check credentials")
        return 1

    log.info(f"Total listings to evaluate: {len(listings)}")

    # --- Price check ---
    feedback = get_feedback_examples() if not dry_run else {}
    wh_bargains, wh_bundles, fa_bargains, fa_bundles = find_bargains(listings, feedback=feedback)
    all_bargains = wh_bargains + fa_bargains

    # Cross-source confirmation (same ISBN on multiple sources → stronger signal)
    _mark_multi_source(listings, all_bargains)

    # Stale detection (URL was alerted before — may not have sold)
    stale_urls = get_previously_alerted_urls([b.listing.url for b in all_bargains]) if not dry_run else set()
    for bargain in all_bargains:
        if bargain.listing.url in stale_urls:
            bargain.stale = True
            log.info(f"Stale listing: {bargain.listing.title!r}")

    enrich_bargains(all_bargains)
    log.info(
        f"Warhammer — bargains: {len(wh_bargains)}, bundles: {len(wh_bundles)} | "
        f"Fantasy — bargains: {len(fa_bargains)}, bundles: {len(fa_bundles)}"
    )

    if dry_run:
        if wh_bargains:
            log.info("Dry-run Warhammer bargains:\n" + format_bargains(wh_bargains))
        if wh_bundles:
            log.info(f"Dry-run Warhammer bundles: {len(wh_bundles)} found")
        if fa_bargains:
            log.info("Dry-run Fantasy bargains:\n" + format_fantasy_bargains(fa_bargains))
        if fa_bundles:
            log.info(f"Dry-run Fantasy bundles: {len(fa_bundles)} found")
        log.info("=== Warhammer Scout scan complete (DRY RUN) ===")
        return 0

    # --- Record to price history DB ---
    scan_id = record_scan(listings, all_bargains)
    record_source_counts(scan_id, source_listing_counts)

    # --- Vinted health check ---
    vinted_count = source_listing_counts.get("vinted", 0)
    if vinted_count == 0:
        recent = get_recent_source_counts("vinted", limit=config.VINTED_ZERO_ALERT_RUNS)
        if len(recent) >= config.VINTED_ZERO_ALERT_RUNS and all(c == 0 for c in recent):
            send_bargain_alert(
                "⚠️ Warhammer Scout — Vinted returned 0 listings for "
                f"{config.VINTED_ZERO_ALERT_RUNS} scans in a row.\n"
                "The session cookie may have expired. Check Vinted access."
            )
            log.warning("Vinted health alert sent — 0 listings for multiple consecutive scans")

    # --- Deduplicate and notify — Warhammer ---
    new_wh_urls = filter_new_alerts(
        [b.listing.url for b in wh_bargains], config.ALERT_DEDUP_DAYS
    )
    new_wh_bargains = [b for b in wh_bargains if b.listing.url in new_wh_urls]
    skipped = len(wh_bargains) - len(new_wh_bargains)
    if skipped:
        log.info(f"Dedup: {skipped} Warhammer bargain(s) suppressed")

    if new_wh_bargains:
        send_bargain_alert(format_bargains(new_wh_bargains))
        record_alerted_urls(new_wh_urls)
        store_alert_positions(scan_id, new_wh_bargains, bot="wh")
    else:
        log.info("No new Warhammer bargains today")

    if wh_bundles:
        new_wh_bundle_urls = filter_new_alerts(
            [b.url for b in wh_bundles], config.ALERT_DEDUP_DAYS
        )
        new_wh_bundles = [b for b in wh_bundles if b.url in new_wh_bundle_urls]
        if new_wh_bundles:
            send_bargain_alert(format_bundles(new_wh_bundles))
            record_alerted_urls(new_wh_bundle_urls)

    # --- Deduplicate and notify — Fantasy/Sci-fi ---
    new_fa_urls = filter_new_alerts(
        [b.listing.url for b in fa_bargains], config.ALERT_DEDUP_DAYS
    )
    new_fa_bargains = [b for b in fa_bargains if b.listing.url in new_fa_urls]
    skipped = len(fa_bargains) - len(new_fa_bargains)
    if skipped:
        log.info(f"Dedup: {skipped} Fantasy bargain(s) suppressed")

    if new_fa_bargains:
        send_fantasy_alert(format_fantasy_bargains(new_fa_bargains))
        record_alerted_urls(new_fa_urls)
        store_alert_positions(scan_id, new_fa_bargains, bot="fa")
    else:
        log.info("No new Fantasy/Sci-fi bargains today")

    if fa_bundles:
        new_fa_bundle_urls = filter_new_alerts(
            [b.url for b in fa_bundles], config.ALERT_DEDUP_DAYS
        )
        new_fa_bundles = [b for b in fa_bundles if b.url in new_fa_bundle_urls]
        if new_fa_bundles:
            send_fantasy_alert(format_fantasy_bundles(new_fa_bundles))
            record_alerted_urls(new_fa_bundle_urls)

    log.info("=== Warhammer Scout scan complete ===")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Warhammer Scout bargain finder")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and price listings but skip Telegram notifications and DB recording",
    )
    args = parser.parse_args()
    setup_logging()
    return run_scan(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
