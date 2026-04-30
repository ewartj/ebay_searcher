"""Buyback price lookup — enriches bargains with WeBuyBooks guaranteed floor prices.

Extracts ISBN-13 or ISBN-10 from listing titles and queries the WeBuyBooks
catalog API. Where a price is found it is stored as buyback_floor on the
Bargain, giving a risk floor: even at worst you can recoup that amount.

ISBNs are rarely present in eBay/Vinted titles, so most lookups short-circuit
at the regex stage with no HTTP call made. All network errors are silently
swallowed — the feature is purely informational.
"""
import logging
import re

import httpx

from models import Bargain

log = logging.getLogger(__name__)

_ISBN13_RE = re.compile(r"\b97[89]\d{10}\b")
_ISBN10_RE = re.compile(r"\b\d{9}[\dX]\b")

_WBB_URL = "https://www.webuybooks.co.uk/api/lookup/"


def extract_isbn(title: str) -> str | None:
    m = _ISBN13_RE.search(title)
    if m:
        return m.group()
    m = _ISBN10_RE.search(title)
    if m:
        return m.group()
    return None


def _lookup_wbb(isbn: str, client: httpx.Client) -> float | None:
    try:
        resp = client.get(_WBB_URL, params={"barcode": isbn}, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            for key in ("price", "sell_price", "amount", "buy_price"):
                if key in data:
                    return float(data[key])
    except Exception as e:
        log.debug(f"WeBuyBooks lookup failed for ISBN {isbn}: {e}")
    return None


def enrich_bargains(bargains: list[Bargain]) -> None:
    """Mutates bargain.buyback_floor in-place for bargains that have an ISBN.

    Uses listing.isbn (structured field from eBay/Biblio) first, then falls
    back to regex extraction from the title.
    """
    if not bargains:
        return

    with httpx.Client(timeout=10) as client:
        for bargain in bargains:
            isbn = bargain.listing.isbn or extract_isbn(bargain.listing.title)
            if not isbn:
                continue
            price = _lookup_wbb(isbn, client)
            if price is not None:
                bargain.buyback_floor = price
                log.info(
                    f"Buyback floor: {bargain.listing.title!r} "
                    f"ISBN {isbn} → £{price:.2f}"
                )
