#!/usr/bin/env python3
"""
Warhammer Scout — daily eBay + Vinted bargain finder for Black Library books.

Run manually:   python main.py
Run dry-run:    python main.py --dry-run
Run daily:      cron / systemd timer (see README)
"""
import argparse
import logging
import logging.handlers
import sys
from pathlib import Path

import config
from db import (
    filter_new_alerts,
    get_recent_source_counts,
    init_db,
    record_alerted_urls,
    record_scan,
    record_source_counts,
)
from notifier import format_bargains, format_bundles, send_bargain_alert
from pricing import find_bargains
from sources import SOURCES

_LOG_FILE = Path(__file__).parent / "data" / "warhammer_scout.log"


def _setup_logging() -> None:
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    console = logging.StreamHandler()
    console.setFormatter(fmt)

    # Rotating file — 1 MB per file, keep last 7
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE, maxBytes=1_000_000, backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    logging.basicConfig(level=logging.INFO, handlers=[console, file_handler])
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def main() -> int:
    parser = argparse.ArgumentParser(description="Warhammer Scout bargain finder")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and price listings but skip Telegram notifications and DB recording",
    )
    args = parser.parse_args()

    _setup_logging()
    log = logging.getLogger("warhammer_scout")

    if args.dry_run:
        log.info("=== Warhammer Scout scan starting (DRY RUN — no notifications) ===")
    else:
        try:
            config.validate()
        except ValueError as e:
            log.error(f"Configuration error: {e}")
            return 1
        log.info("=== Warhammer Scout scan starting ===")
        init_db()

    listings = []
    source_listing_counts: dict[str, int] = {}

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

    if not listings:
        log.warning("No listings retrieved from any source — check credentials")
        return 1

    log.info(f"Total listings to evaluate: {len(listings)}")

    # --- Price check ---
    bargains, bundles = find_bargains(listings)
    log.info(f"Bargains found: {len(bargains)}, bundles for review: {len(bundles)}")

    if args.dry_run:
        if bargains:
            log.info("Dry-run bargains:\n" + format_bargains(bargains))
        if bundles:
            log.info(f"Dry-run bundles: {len(bundles)} found")
        log.info("=== Warhammer Scout scan complete (DRY RUN) ===")
        return 0

    # --- Record to price history DB ---
    scan_id = record_scan(listings, bargains)
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

    # --- Deduplicate bargains against previously alerted URLs ---
    new_bargain_urls = filter_new_alerts(
        [b.listing.url for b in bargains], config.ALERT_DEDUP_DAYS
    )
    new_bargains = [b for b in bargains if b.listing.url in new_bargain_urls]

    skipped = len(bargains) - len(new_bargains)
    if skipped:
        log.info(f"Dedup: {skipped} previously alerted bargain(s) suppressed")

    # --- Notify ---
    if new_bargains:
        send_bargain_alert(format_bargains(new_bargains))
        record_alerted_urls(new_bargain_urls)
    else:
        log.info("No new bargains today — no notification sent")

    if bundles:
        new_bundle_urls = filter_new_alerts(
            [b.url for b in bundles], config.ALERT_DEDUP_DAYS
        )
        new_bundles = [b for b in bundles if b.url in new_bundle_urls]
        if new_bundles:
            send_bargain_alert(format_bundles(new_bundles))
            record_alerted_urls(new_bundle_urls)

    log.info("=== Warhammer Scout scan complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
