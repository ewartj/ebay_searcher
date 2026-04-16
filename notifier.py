"""Telegram notification — sends a daily bargain summary to your phone."""
import logging

import httpx

import config
from models import Bargain

log = logging.getLogger(__name__)

_TELEGRAM_URL = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"


def format_bargains(bargains: list[Bargain]) -> str:
    """Format bargains as plain text for Telegram."""
    lines = [f"Warhammer Scout — {len(bargains)} bargain(s) found today\n"]

    for i, b in enumerate(bargains, 1):
        source = "eBay" if b.listing.source == "ebay" else "Vinted"
        lines.append(
            f"{i}. [{source}] {b.listing.title}\n"
            f"   £{b.listing.price_gbp:.2f} (market ~£{b.market_price:.2f})"
            f" — {b.discount_pct:.0%} off\n"
            f"   {b.listing.url}"
        )

    return "\n".join(lines)


def send_telegram_message(text: str) -> None:
    """Send a message to the configured Telegram chat."""
    try:
        resp = httpx.post(
            _TELEGRAM_URL,
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        resp.raise_for_status()
        log.info("Telegram message sent successfully")
    except httpx.HTTPStatusError as e:
        log.error(f"Telegram notification failed: HTTP {e.response.status_code} — {e.response.text}")
    except httpx.HTTPError:
        log.error("Telegram notification failed: connection error")
