"""Telegram notification — sends a daily bargain summary to your phone."""
import logging

import httpx

import config
from models import Bargain, Listing

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


def format_bundles(bundles: list[Listing]) -> str:
    """Format bundle listings as plain text for manual review."""
    lines = [f"Warhammer Scout — {len(bundles)} bundle(s) to review\n"]

    for i, b in enumerate(bundles, 1):
        source = "eBay" if b.source == "ebay" else "Vinted"
        lines.append(
            f"{i}. [{source}] {b.title}\n"
            f"   £{b.price_gbp:.2f}\n"
            f"   {b.url}"
        )

    return "\n".join(lines)


_MAX_LENGTH = 4096


def _split_message(text: str) -> list[str]:
    """Split a message into Telegram-sized chunks, breaking on newlines."""
    if len(text) <= _MAX_LENGTH:
        return [text]

    chunks = []
    while text:
        if len(text) <= _MAX_LENGTH:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, _MAX_LENGTH)
        if split_at == -1:
            split_at = _MAX_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    return chunks


def send_telegram_message(text: str) -> None:
    """Send a message to the configured Telegram chat, splitting if over 4096 chars."""
    chunks = _split_message(text)
    for i, chunk in enumerate(chunks, 1):
        try:
            resp = httpx.post(
                _TELEGRAM_URL,
                json={
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            resp.raise_for_status()
            if len(chunks) > 1:
                log.info(f"Telegram message sent ({i}/{len(chunks)})")
            else:
                log.info("Telegram message sent successfully")
        except httpx.HTTPStatusError as e:
            log.error(f"Telegram notification failed: HTTP {e.response.status_code} — {e.response.text}")
            return
        except httpx.HTTPError:
            log.error("Telegram notification failed: connection error")
            return
