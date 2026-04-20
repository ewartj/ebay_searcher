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
from db import init_db, record_scan
from notifier import format_bargains, format_bundles, send_telegram_message
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
        log.info("=== Warhammer Scout scan starting ===")
        init_db()

    listings = []

    for source_name, fetch in SOURCES.items():
        try:
            fetched = fetch()
            log.info(f"{source_name}: {len(fetched)} listings fetched")
            listings.extend(fetched)
        except Exception as e:
            log.error(f"{source_name} source failed: {e}")

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
    record_scan(listings, bargains)

    # --- Notify ---
    if bargains:
        send_telegram_message(format_bargains(bargains))
    else:
        log.info("No bargains today — no notification sent")

    if bundles:
        send_telegram_message(format_bundles(bundles))

    log.info("=== Warhammer Scout scan complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
