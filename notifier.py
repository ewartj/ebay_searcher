"""Telegram notifications — bargain alerts and weekly market digest."""
import logging

import httpx

import config
from models import Bargain, Listing

log = logging.getLogger(__name__)

# Maps internal source name to the display label used in notifications.
# Add an entry here whenever a new source is added to sources/__init__.py.
_SOURCE_LABEL: dict[str, str] = {
    "ebay": "eBay",
    "vinted": "Vinted",
}


def _label(source: str) -> str:
    return _SOURCE_LABEL.get(source, source.title())


def format_bargains(bargains: list[Bargain]) -> str:
    """Format bargains as plain text for Telegram."""
    lines = [f"Warhammer Scout — {len(bargains)} bargain(s) found today\n"]

    for i, b in enumerate(bargains, 1):
        lines.append(
            f"{i}. [{_label(b.listing.source)}] {b.listing.title}\n"
            f"   £{b.listing.price_gbp:.2f} (market ~£{b.market_price:.2f})"
            f" — {b.discount_pct:.0%} off\n"
            f"   {b.listing.url}"
        )

    return "\n".join(lines)


def format_bundles(bundles: list[Listing]) -> str:
    """Format bundle listings as plain text for manual review."""
    lines = [f"Warhammer Scout — {len(bundles)} bundle(s) to review\n"]

    for i, b in enumerate(bundles, 1):
        lines.append(
            f"{i}. [{_label(b.source)}] {b.title}\n"
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


def send_telegram_message(text: str, *, bot_token: str, chat_id: str) -> None:
    """Send a message to a Telegram chat, splitting if over 4096 chars."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    chunks = _split_message(text)
    for i, chunk in enumerate(chunks, 1):
        try:
            resp = httpx.post(
                url,
                json={
                    "chat_id": chat_id,
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
            masked = f"...{chat_id[-4:]}" if len(chat_id) > 4 else "****"
            log.error(
                f"Telegram notification failed: HTTP {e.response.status_code} — "
                f"{e.response.text} (chat_id={masked})"
            )
            return
        except httpx.HTTPError:
            log.error("Telegram notification failed: connection error")
            return


def send_bargain_alert(text: str) -> None:
    """Send to the Warhammer bargain alerts channel (daily buys)."""
    send_telegram_message(text, bot_token=config.TELEGRAM_BOT_TOKEN, chat_id=config.TELEGRAM_CHAT_ID)


def send_digest_alert(text: str) -> None:
    """Send to the market research channel (weekly digest)."""
    send_telegram_message(
        text,
        bot_token=config.TELEGRAM_DIGEST_BOT_TOKEN,
        chat_id=config.TELEGRAM_DIGEST_CHAT_ID,
    )


def format_fantasy_bargains(bargains: list[Bargain]) -> str:
    """Format fantasy/sci-fi bargains as plain text for Telegram."""
    lines = [f"Fantasy Scout — {len(bargains)} bargain(s) found today\n"]

    for i, b in enumerate(bargains, 1):
        lines.append(
            f"{i}. [{_label(b.listing.source)}] {b.listing.title}\n"
            f"   £{b.listing.price_gbp:.2f} (market ~£{b.market_price:.2f})"
            f" — {b.discount_pct:.0%} off\n"
            f"   {b.listing.url}"
        )

    return "\n".join(lines)


def format_fantasy_bundles(bundles: list[Listing]) -> str:
    """Format fantasy/sci-fi bundle listings as plain text for manual review."""
    lines = [f"Fantasy Scout — {len(bundles)} bundle(s) to review\n"]

    for i, b in enumerate(bundles, 1):
        lines.append(
            f"{i}. [{_label(b.source)}] {b.title}\n"
            f"   £{b.price_gbp:.2f}\n"
            f"   {b.url}"
        )

    return "\n".join(lines)


def send_fantasy_alert(text: str) -> None:
    """Send to the fantasy & sci-fi bargain alerts channel.
    No-ops silently if TELEGRAM_FANTASY_BOT_TOKEN / CHAT_ID are not configured.
    """
    if not config.TELEGRAM_FANTASY_BOT_TOKEN or not config.TELEGRAM_FANTASY_CHAT_ID:
        log.debug("Fantasy Telegram bot not configured — skipping fantasy alert")
        return
    send_telegram_message(
        text,
        bot_token=config.TELEGRAM_FANTASY_BOT_TOKEN,
        chat_id=config.TELEGRAM_FANTASY_CHAT_ID,
    )
