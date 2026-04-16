#!/usr/bin/env python3
"""
Warhammer Scout — daily eBay + Vinted bargain finder for Black Library books.

Run manually:   python main.py
Run daily:      cron / systemd timer (see README)
"""
import logging
import sys

from notifier import format_bargains, send_telegram_message
from pricing import find_bargains
from sources.ebay import fetch_ebay_listings
from sources.vinted import fetch_vinted_listings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Suppress httpx request logs — they expose API keys in query params
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("warhammer_scout")


def main() -> int:
    log.info("=== Warhammer Scout scan starting ===")

    listings = []

    # --- eBay ---
    try:
        ebay_listings = fetch_ebay_listings()
        log.info(f"eBay: {len(ebay_listings)} listings fetched")
        listings.extend(ebay_listings)
    except Exception as e:
        log.error(f"eBay source failed: {e}")

    # --- Vinted ---
    try:
        vinted_listings = fetch_vinted_listings()
        log.info(f"Vinted: {len(vinted_listings)} listings fetched")
        listings.extend(vinted_listings)
    except Exception as e:
        log.error(f"Vinted source failed: {e}")

    if not listings:
        log.warning("No listings retrieved from any source — check credentials")
        return 1

    log.info(f"Total listings to evaluate: {len(listings)}")

    # --- Price check ---
    bargains = find_bargains(listings)
    log.info(f"Bargains found: {len(bargains)}")

    # --- Notify ---
    if bargains:
        message = format_bargains(bargains)
        send_telegram_message(message)
    else:
        log.info("No bargains today — no notification sent")

    log.info("=== Warhammer Scout scan complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
