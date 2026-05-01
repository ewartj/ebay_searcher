"""Telegram notifications — bargain alerts and weekly market digest."""
import logging

import httpx

import config
from db import get_last_alert_positions, get_setting, set_setting, store_feedback
from models import Bargain, Listing

log = logging.getLogger(__name__)

# Maps internal source name to the display label used in notifications.
# Add an entry here whenever a new source is added to sources/__init__.py.
_SOURCE_LABEL: dict[str, str] = {
    "ebay": "eBay",
    "vinted": "Vinted",
    "etsy": "Etsy",
}


def _label(source: str) -> str:
    return _SOURCE_LABEL.get(source, source.title())


def format_bargains(bargains: list[Bargain]) -> str:
    """Format bargains as plain text for Telegram."""
    lines = [f"Warhammer Scout — {len(bargains)} bargain(s) found today\n"]

    for i, b in enumerate(bargains, 1):
        floor = f" | floor £{b.buyback_floor:.2f}" if b.buyback_floor else ""
        flags = []
        if b.multi_source:
            flags.append("multi-source")
        if b.stale:
            flags.append("seen before")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        lines.append(
            f"{i}.{flag_str} [{_label(b.listing.source)}] {b.listing.title}\n"
            f"   £{b.listing.price_gbp:.2f} (market ~£{b.market_price:.2f}"
            f"{floor}) — {b.discount_pct:.0%} off\n"
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
        floor = f" | floor £{b.buyback_floor:.2f}" if b.buyback_floor else ""
        flags = []
        if b.multi_source:
            flags.append("multi-source")
        if b.stale:
            flags.append("seen before")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        lines.append(
            f"{i}.{flag_str} [{_label(b.listing.source)}] {b.listing.title}\n"
            f"   £{b.listing.price_gbp:.2f} (market ~£{b.market_price:.2f}"
            f"{floor}) — {b.discount_pct:.0%} off\n"
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


def poll_feedback(bot_token: str, chat_id: str, bot: str = "wh") -> int:
    """Poll Telegram for /good and /bad commands, store results in DB.

    Users reply to their bargain alert with:
      /good        — marks all items in the last alert as confirmed buys
      /good 1 3    — marks items 1 and 3 as confirmed buys
      /bad 2       — marks item 2 as a false positive

    Returns the number of feedback items recorded.
    """
    if not bot_token or not chat_id:
        return 0

    offset_key = f"tg_offset_{bot}"
    offset = int(get_setting(offset_key, "0"))
    positions = get_last_alert_positions(bot)

    try:
        resp = httpx.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            params={"offset": offset, "timeout": 0, "limit": 100},
            timeout=10,
        )
        resp.raise_for_status()
        updates = resp.json().get("result", [])
    except Exception as e:
        # Log only the exception type — the URL contains the live bot token
        log.warning(f"Telegram feedback poll failed ({bot}): {type(e).__name__}")
        return 0

    count = 0
    new_offset = offset

    for update in updates:
        new_offset = max(new_offset, update["update_id"] + 1)
        message = update.get("message", {})
        if str(message.get("chat", {}).get("id", "")) != str(chat_id):
            continue

        text = (message.get("text") or "").strip().lower()
        if text.startswith("/good"):
            outcome = "good"
        elif text.startswith("/bad"):
            outcome = "bad"
        else:
            continue

        parts = text.split(None, 1)
        if len(parts) > 1:
            raw_nums = parts[1].replace(",", " ").split()
            nums = [int(n) for n in raw_nums if n.isdigit()]
        else:
            nums = list(positions.keys())

        for pos in nums:
            if pos in positions:
                url, title = positions[pos]
                store_feedback(url, title, outcome)
                count += 1

    if new_offset != offset:
        set_setting(offset_key, str(new_offset))

    if count:
        log.info(f"Feedback: recorded {count} item(s) from Telegram ({bot})")
    return count


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
