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

# --- Telegram — bargain alerts (daily buys) ---
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]

# --- Telegram — market research digest (weekly) ---
TELEGRAM_DIGEST_BOT_TOKEN: str = os.environ["TELEGRAM_DIGEST_BOT_TOKEN"]
TELEGRAM_DIGEST_CHAT_ID: str = os.environ["TELEGRAM_DIGEST_CHAT_ID"]

# Flag a listing as a bargain if its price is at or below this fraction of market value.
# 0.70 = 30% below market
# How many days before a previously alerted listing URL can be alerted again.
# Handles relists — a book relisted after 30 days is worth flagging again.
ALERT_DEDUP_DAYS: int = 30

# Minimum acceptable listing condition. Skip anything below these thresholds.
# eBay book conditions (best → worst): New, Like New, Very Good, Good, Acceptable
# Vinted conditions: new_with_tags, new_without_tags, very_good, good, satisfactory
# Title keywords that identify non-prose items to exclude from pricing entirely.
# These match in pricing.py before any API calls are made.
# Add terms here if new junk categories start appearing in search results.
EXCLUDE_TITLE_KEYWORDS: list[str] = [
    "codex", "codices", "rulebook", "rule book",
    "art book", "artbook", "painting guide", "painting manual",
    "warhammer legends", "army guide", "starter set", "starter box",
    "index astartes",
]

ACCEPTED_EBAY_CONDITIONS: set[str] = {"New", "Like New", "Very Good", "Good"}
ACCEPTED_VINTED_CONDITIONS: set[str] = {"new_with_tags", "new_without_tags", "very_good", "good"}

# Warn via Telegram if Vinted returns 0 listings this many scans in a row
# (usually means the session cookie has expired)
VINTED_ZERO_ALERT_RUNS: int = 2

BARGAIN_THRESHOLD: float = 0.70

# Minimum expected profit (market price minus listing price) to flag as a bargain.
# Filters out technically discounted but low-value listings.
MIN_PROFIT: float = 10.0

# Search terms used on eBay — (term, max_results) pairs.
# Broad terms get fewer results to avoid noise; focused terms get more.
SEARCH_TERMS: list[tuple[str, int]] = [
    ("black library hardback",               50),
    ("black library limited edition",        50),
    ("horus heresy hardback",                50),
    ("black library signed",                 50),
    ("warhammer black library omnibus hardback", 50),
    ("job lot black library",                10),
    ("horus heresy books",                   10),
]

# Search terms used on Vinted — (term, max_results) pairs.
VINTED_SEARCH_TERMS: list[tuple[str, int]] = [
    ("black library hardback",    50),
    ("horus heresy hardback",     50),
    ("warhammer hardback",        50),
    ("black library limited",     50),
    ("black library signed",      50),
    ("job lot black library",     10),
    ("horus heresy books",        10),
]


# Weekly genre price tracking — fantasy/sci-fi authors and series.
# (search_term, display_label) — run by scripts/genre_tracker.py
GENRE_SEARCH_TERMS: list[tuple[str, str]] = [
    # Grimdark / Epic Fantasy
    ("joe abercrombie hardback",         "Joe Abercrombie"),
    ("brandon sanderson hardback",        "Brandon Sanderson"),
    ("robin hobb hardback",               "Robin Hobb"),
    ("steven erikson malazan hardback",   "Steven Erikson / Malazan"),
    ("patrick rothfuss hardback",         "Patrick Rothfuss"),
    ("mark lawrence hardback",            "Mark Lawrence"),
    ("michael j sullivan hardback",       "Michael J. Sullivan"),
    # Classic / New Space Opera
    ("iain m banks hardback",             "Iain M. Banks"),
    ("peter f hamilton hardback",         "Peter F. Hamilton"),
    ("alastair reynolds hardback",        "Alastair Reynolds"),
    ("richard morgan altered carbon",     "Richard Morgan"),
    # Collectible / Popular
    ("terry pratchett hardback signed",   "Terry Pratchett"),
    ("neil gaiman hardback",              "Neil Gaiman"),
    ("gene wolfe hardback",               "Gene Wolfe"),
    ("ursula le guin hardback",           "Ursula K. Le Guin"),
    # Key Series
    ("first law hardback abercrombie",    "First Law"),
    ("stormlight archive hardback",       "Stormlight Archive"),
    ("kingkiller chronicle hardback",     "Kingkiller Chronicle"),
    ("name of the wind hardback",         "Name of the Wind"),
]

# Subreddits monitored for market signals (via RSS, old.reddit.com) — run by scripts/weekly_digest.py
REDDIT_SUBREDDITS: list[str] = [
    # Black Library / Warhammer
    "BlackLibrary",
    "warhammer",
    "warhammer40k",
    "40klore",
    "HorusHeresyLegions",
    # Fantasy / Sci-fi
    "fantasy",
    "printSF",
    "sciencefiction",
    "scifi",
    "books",
]

# Publisher and trade RSS feeds — (display_name, feed_url)
NEWS_FEEDS: list[tuple[str, str]] = [
    ("The Guardian Books", "https://www.theguardian.com/books/rss"),
    ("Locus Magazine",     "https://locusmag.com/feed/"),
    ("io9",                "https://io9.gizmodo.com/rss"),
]


def validate() -> None:
    """Raise ValueError if any required credential is missing or placeholder."""
    required = {
        "EBAY_CLIENT_ID": EBAY_CLIENT_ID,
        "EBAY_CLIENT_SECRET": EBAY_CLIENT_SECRET,
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
        "TELEGRAM_DIGEST_BOT_TOKEN": TELEGRAM_DIGEST_BOT_TOKEN,
        "TELEGRAM_DIGEST_CHAT_ID": TELEGRAM_DIGEST_CHAT_ID,
    }
    missing = [name for name, val in required.items() if not val]
    if missing:
        raise ValueError(f"Missing required config: {', '.join(missing)}")
