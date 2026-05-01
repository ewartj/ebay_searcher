"""Configuration — credentials, thresholds, and search terms."""
import os
from pathlib import Path
from dotenv import load_dotenv

from price_guide import PRICE_GUIDE  # noqa: F401 — re-exported for use across the app
from price_guide_fantasy import FANTASY_PRICE_GUIDE  # noqa: F401 — re-exported for use across the app

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

# --- Telegram — fantasy & sci-fi bargain alerts ---
TELEGRAM_FANTASY_BOT_TOKEN: str = os.environ.get("TELEGRAM_FANTASY_BOT_TOKEN", "")
TELEGRAM_FANTASY_CHAT_ID: str = os.environ.get("TELEGRAM_FANTASY_CHAT_ID", "")

# --- Etsy API (etsy.com/developers) ---
# Optional — set to enable the Etsy source. Skips silently when empty.
ETSY_API_KEY: str = os.environ.get("ETSY_API_KEY", "")


# --- Lambda / deployment ---
# True when running inside AWS Lambda
IS_LAMBDA: bool = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

# SQLite database path.
# Defaults to /tmp/prices.db in Lambda (only writable location),
# or data/prices.db next to this file for local runs.
_default_db_path = (
    "/tmp/prices.db"
    if IS_LAMBDA
    else str(Path(__file__).parent / "data" / "prices.db")
)
DB_PATH: str = os.environ.get("DB_PATH", _default_db_path)

# S3 bucket and key for persisting the SQLite DB between Lambda invocations.
# Leave S3_BUCKET empty when running locally.
S3_BUCKET: str = os.environ.get("S3_BUCKET", "")
S3_DB_KEY: str = os.environ.get("S3_DB_KEY", "warhammer-scout/prices.db")

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
    "art book", "artbook", "art print", "a3 art", "a4 art", "a2 art",
    "poster", "print set",
    "painting guide", "painting manual",
    "warhammer legends", "army guide", "starter set", "starter box",
    "index astartes",
    "tour stamp", "event stamp", "bookplate",
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
    ("job lot black library",                20),
    ("horus heresy books",                   20),
    ("horus heresy bundle",                  20),
    ("black library bundle",                 20),
    ("warhammer book bundle",                20),
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


# Etsy search terms — (term, max_results) pairs.
ETSY_SEARCH_TERMS: list[tuple[str, int]] = [
    ("black library hardback signed",      30),
    ("horus heresy hardback",              30),
    ("warhammer hardback book",            20),
    ("black library limited edition",      30),
]

# Etsy fantasy & sci-fi search terms.
ETSY_FANTASY_SEARCH_TERMS: list[tuple[str, int]] = [
    ("fantasy hardback signed first edition", 20),
    ("joe abercrombie hardback",              20),
    ("brandon sanderson hardback",            20),
    ("terry pratchett signed hardback",       20),
    ("neil gaiman signed hardback",           20),
]

# Fantasy & sci-fi eBay search terms — routed to the fantasy Telegram bot.
FANTASY_SEARCH_TERMS: list[tuple[str, int]] = [
    # Joe Abercrombie
    ("joe abercrombie hardback",            30),
    ("first law hardback",                  30),
    # Brandon Sanderson
    ("brandon sanderson hardback",          30),
    ("stormlight archive hardback",         30),
    ("mistborn hardback",                   30),
    # Dragonlance
    ("dragonlance hardback",                20),
    ("dragonlance chronicles hardback",     20),
    # Patrick Rothfuss
    ("name of the wind hardback",           20),
    ("patrick rothfuss hardback",           20),
    # Robin Hobb
    ("robin hobb hardback",                 30),
    ("farseer hardback",                    20),
    # Steven Erikson / Malazan
    ("steven erikson hardback",             20),
    ("malazan hardback",                    20),
    # Iain M. Banks / Culture
    ("iain m banks hardback",               20),
    ("culture series hardback",             20),
    # Terry Pratchett & Neil Gaiman (signed/collectible)
    ("terry pratchett signed hardback",     20),
    ("neil gaiman signed hardback",         20),
    # Peter F. Hamilton
    ("peter f hamilton hardback",           20),
    # Alastair Reynolds
    ("alastair reynolds hardback",          20),
    # Mark Lawrence
    ("mark lawrence hardback",              20),
    # Subscription box special editions
    ("illumicrate hardback",               30),
    ("illumicrate signed",                 30),
    ("owlcrate hardback",                  20),
    ("owlcrate signed",                    20),
    ("fairyloot hardback",                 20),
    ("fairyloot signed",                   20),
    # Authors common in subscription boxes not otherwise covered
    ("v e schwab hardback",                20),
    ("leigh bardugo hardback",             20),
    ("sarah j maas hardback",              20),
    ("r f kuang hardback",                 20),
    ("samantha shannon hardback",          15),
    ("naomi novik hardback signed",        15),
    # Bundles
    ("job lot fantasy hardback",            10),
    ("job lot sci-fi hardback",             10),
]

# Fantasy & sci-fi Vinted search terms.
FANTASY_VINTED_SEARCH_TERMS: list[tuple[str, int]] = [
    ("joe abercrombie hardback",            30),
    ("first law hardback",                  30),
    ("brandon sanderson hardback",          30),
    ("stormlight archive hardback",         30),
    ("mistborn hardback",                   20),
    ("dragonlance hardback",                20),
    ("name of the wind hardback",           20),
    ("robin hobb hardback",                 30),
    ("iain m banks hardback",               20),
    ("terry pratchett signed hardback",     20),
    ("neil gaiman signed hardback",         20),
    ("malazan hardback",                    20),
    ("illumicrate hardback",               20),
    ("illumicrate signed",                 20),
    ("owlcrate hardback",                  15),
    ("fairyloot hardback",                 15),
    ("v e schwab hardback",                15),
    ("leigh bardugo hardback",             15),
    ("sarah j maas hardback",              15),
    ("job lot fantasy hardback",            10),
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

# Candidate niches probed weekly by scripts/market_scout.py.
# Add any niche you're curious about — the scout scores each by price variance
# and liquidity, then Claude surfaces the best opportunities.
# (search_term, display_label)
NICHE_SCOUT_TERMS: list[tuple[str, str]] = [
    # Small-press limited editions (horror / SF)
    ("subterranean press horror hardback",      "Subterranean Press Horror"),
    ("cemetery dance signed hardback",          "Cemetery Dance Signed"),
    ("ps publishing signed hardback",           "PS Publishing Signed"),
    ("tor signed hardback limited edition",     "Tor Signed Limited"),

    # UK signed-edition specialists
    ("goldsboro books signed hardback",         "Goldsboro Signed"),
    ("forbidden planet exclusive hardback",     "Forbidden Planet Exclusive"),

    # Leather-bound collectibles
    ("easton press leather bound hardback",     "Easton Press Leather"),
    ("franklin library leather hardback",       "Franklin Library"),

    # Vintage UK SF / horror anthologies
    ("gollancz sf masterworks hardback",        "Gollancz SF Masterworks"),
    ("pan horror anthology vintage",            "Pan Horror Vintage"),
    ("fontana horror anthology vintage",        "Fontana Horror Vintage"),
    ("victor gollancz first edition hardback",  "Gollancz First Edition"),

    # Horror authors (not in daily/weekly scans)
    ("stephen king limited edition hardback",   "Stephen King Limited"),
    ("clive barker signed hardback",            "Clive Barker Signed"),
    ("ramsey campbell signed hardback",         "Ramsey Campbell Signed"),
    ("james herbert hardback signed",           "James Herbert Signed"),

    # Classic SF authors not yet tracked
    ("isaac asimov hardback foundation",        "Asimov Foundation Hardback"),
    ("arthur c clarke hardback signed",         "Arthur C. Clarke Signed"),
    ("philip k dick hardback",                  "Philip K. Dick Hardback"),
    ("michael moorcock hardback elric",         "Moorcock / Elric Hardback"),
    ("david gemmell hardback signed",           "David Gemmell Signed"),
    ("roger zelazny hardback amber",            "Zelazny / Amber Hardback"),

    # Popular fantasy authors not in FANTASY_SEARCH_TERMS
    ("raymond feist hardback riftwar",          "Feist / Riftwar Hardback"),
    ("david eddings hardback belgariad",        "Eddings / Belgariad Hardback"),
    ("anne mccaffrey hardback dragonriders",    "McCaffrey Dragonriders Hardback"),
    ("guy gavriel kay hardback signed",         "Guy Gavriel Kay Signed"),
    ("china mieville signed hardback",          "China Miéville Signed"),
    ("susanna clarke signed hardback",          "Susanna Clarke Signed"),
    ("philip pullman signed hardback",          "Philip Pullman Signed"),

    # Wargaming crossover / RPG hardbacks
    ("warhammer fantasy roleplay hardback",     "WFRP Hardback"),
    ("osprey wargames hardback",                "Osprey Wargames"),
    ("dungeons dragons first edition",          "D&D 1e/2e"),
    ("call of cthulhu hardback",                "Call of Cthulhu Hardback"),
    ("vampire masquerade hardback",             "Vampire: The Masquerade"),
    ("realm of chaos hardback warhammer",       "Realm of Chaos Original"),

    # Comics / graphic novel hardbacks
    ("2000 ad graphic novel hardback",          "2000 AD Hardback"),
    ("judge dredd collection hardback",         "Judge Dredd Collection"),
    ("alan moore hardback signed",              "Alan Moore Signed"),
    ("sandman deluxe hardback gaiman",          "Sandman Deluxe"),
    ("preacher complete hardback garth ennis",  "Preacher Complete"),
    ("hellboy library edition hardback",        "Hellboy Library Edition"),

    # Deluxe manga editions
    ("berserk deluxe hardback english",         "Berserk Deluxe"),
    ("vagabond hardback english",               "Vagabond Hardback"),
    ("vinland saga hardback deluxe",            "Vinland Saga Deluxe"),
    ("manga box set english out of print",      "Manga Box Sets OOP"),

    # Classic collectibles
    ("fighting fantasy hardback",               "Fighting Fantasy"),
    ("discworld hardback signed",               "Discworld Signed"),
    ("lord of the rings limited edition",       "LOTR Limited Editions"),
    ("dune hardback limited edition",           "Dune Limited Editions"),
    ("hitchhikers guide signed hardback",       "Hitchhiker's Guide Signed"),
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
