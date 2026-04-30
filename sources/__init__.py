"""
Source registry — maps source name to its fetch function.

To add a new source (e.g. Abe Books):
  1. Create sources/abebooks.py with a fetch_abebooks_listings() function
  2. Add an entry here: "abebooks": fetch_abebooks_listings
  3. Add ABEBOOKS_SEARCH_TERMS to config.py
  That's it — main.py and notifier.py need no changes.
"""
from collections.abc import Callable

from models import Listing
from sources.ebay import fetch_ebay_listings
from sources.etsy import fetch_etsy_listings
from sources.vinted import fetch_vinted_listings

SOURCES: dict[str, Callable[[], list[Listing]]] = {
    "ebay": fetch_ebay_listings,
    "vinted": fetch_vinted_listings,
    "etsy": fetch_etsy_listings,
}
