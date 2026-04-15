"""Configuration — edit PRICE_GUIDE and SEARCH_TERMS to match your inventory knowledge."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- eBay API (developer.ebay.com) ---
EBAY_CLIENT_ID: str = os.environ["EBAY_CLIENT_ID"]
EBAY_CLIENT_SECRET: str = os.environ["EBAY_CLIENT_SECRET"]

# --- Google Gemini (aistudio.google.com) ---
GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]

# --- Telegram bot ---
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]

# Flag a listing as a bargain if its price is at or below this fraction of market value.
# 0.70 = 30% below market
BARGAIN_THRESHOLD: float = 0.70

# Search terms run on both eBay and Vinted.
# Keep these specific enough to avoid noise.
SEARCH_TERMS: list[str] = [
    "black library hardback",
    "black library limited edition",
    "horus heresy hardback",
    "black library signed",
    "warhammer black library omnibus hardback",
]

# ---------------------------------------------------------------------------
# Known market values (GBP) for commonly traded Black Library titles.
# Key = lowercase substring that must appear anywhere in the listing title.
# Add / adjust these with your own market knowledge — you know the market
# better than any API.  Matching is substring, so "horus rising" matches
# "Horus Rising: Horus Heresy Book 1 (Hardback)" etc.
# ---------------------------------------------------------------------------
PRICE_GUIDE: dict[str, float] = {
    # Horus Heresy (main series)
    "horus rising": 30.0,
    "false gods": 28.0,
    "galaxy in flames": 28.0,
    "flight of the eisenstein": 28.0,
    "fulgrim": 35.0,
    "descent of angels": 25.0,
    "legion": 40.0,
    "battle for the abyss": 22.0,
    "mechanicum": 35.0,
    "tales of heresy": 25.0,
    "fallen angels": 25.0,
    "a thousand sons": 40.0,
    "nemesis": 30.0,
    "the first heretic": 35.0,
    "prospero burns": 40.0,
    "age of darkness": 28.0,
    "the outcast dead": 28.0,
    "deliverance lost": 28.0,
    "know no fear": 40.0,
    "the primarchs": 35.0,
    "fear to tread": 35.0,
    "shadows of treachery": 28.0,
    "angel exterminatus": 35.0,
    "betrayer": 40.0,
    "mark of calth": 28.0,
    "vulkan lives": 28.0,
    "the unremembered empire": 35.0,
    "scars": 28.0,
    "vengeful spirit": 35.0,
    "the damnation of pythos": 22.0,
    "legacies of betrayal": 28.0,
    "deathfire": 28.0,
    "war without end": 28.0,
    "master of mankind": 45.0,
    "garro": 35.0,
    "shattered legions": 28.0,
    "the crimson king": 38.0,
    "tallarn": 28.0,
    "ruinstorm": 35.0,
    "old earth": 28.0,
    "the burden of loyalty": 28.0,
    "wolfsbane": 35.0,
    "born of flame": 28.0,
    "slaves to darkness": 35.0,
    "malevolence": 35.0,
    "lost and the damned": 40.0,
    "first wall": 40.0,
    "solar war": 45.0,
    "saturnine": 55.0,
    "mortis": 45.0,
    "warhawk": 40.0,
    "echoes of eternity": 40.0,
    "end and the death": 55.0,
    # Siege of Terra
    "siege of terra": 45.0,
    # Eisenhorn / Ravenor / Bequin
    "eisenhorn": 50.0,
    "ravenor rogue": 40.0,
    "ravenor returned": 38.0,
    "ravenor": 40.0,
    "pariah": 35.0,
    "penitent": 35.0,
    "bequin": 35.0,
    # Gaunt's Ghosts
    "first and only": 30.0,
    "ghostmaker": 28.0,
    "necropolis": 35.0,
    "honour guard": 28.0,
    "the guns of tanith": 28.0,
    "straight silver": 28.0,
    "sabbat martyr": 35.0,
    "traitor general": 30.0,
    "his last command": 30.0,
    "the armour of contempt": 30.0,
    "only in death": 30.0,
    "blood pact": 35.0,
    "salvation's reach": 35.0,
    "the warmaster": 40.0,
    "anarch": 40.0,
    "salvations reach": 35.0,
    # Other popular titles
    "titanicus": 35.0,
    "double eagle": 35.0,
    "brothers of the snake": 30.0,
    "xenos": 25.0,
    "malleus": 25.0,
    "hereticus": 25.0,
}
