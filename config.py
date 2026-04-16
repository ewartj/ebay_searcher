"""Configuration — credentials, thresholds, and search terms."""
import os
from dotenv import load_dotenv

from price_guide import PRICE_GUIDE  # noqa: F401 — re-exported for use across the app

load_dotenv()

# --- eBay API (developer.ebay.com) ---
EBAY_CLIENT_ID: str = os.environ["EBAY_CLIENT_ID"]
EBAY_CLIENT_SECRET: str = os.environ["EBAY_CLIENT_SECRET"]

# --- Anthropic (console.anthropic.com) ---
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]

# --- Telegram bot ---
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]

# Flag a listing as a bargain if its price is at or below this fraction of market value.
# 0.70 = 30% below market
BARGAIN_THRESHOLD: float = 0.70

# Search terms used on eBay.
SEARCH_TERMS: list[str] = [
    "black library hardback",
    "black library limited edition",
    "horus heresy hardback",
    "black library signed",
    "warhammer black library omnibus hardback",
]

# Search terms used on Vinted (simpler terms work better — sellers use shorter titles).
VINTED_SEARCH_TERMS: list[str] = [
    "black library hardback",
    "horus heresy hardback",
    "warhammer hardback",
    "black library limited",
    "black library signed",
]


def validate() -> None:
    """Raise ValueError if any required credential is missing or placeholder."""
    required = {
        "EBAY_CLIENT_ID": EBAY_CLIENT_ID,
        "EBAY_CLIENT_SECRET": EBAY_CLIENT_SECRET,
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }
    missing = [name for name, val in required.items() if not val]
    if missing:
        raise ValueError(f"Missing required config: {', '.join(missing)}")
