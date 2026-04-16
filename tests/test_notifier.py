"""Tests for notifier.py — message formatting and splitting."""
import pytest

from models import Bargain, Listing
from notifier import _split_message, format_bargains, format_bundles


def _listing(title: str, price: float, source: str = "ebay", url: str = "https://ebay.co.uk/itm/1") -> Listing:
    return Listing(title=title, price_gbp=price, url=url, source=source)


def _bargain(title: str, listing_price: float, market_price: float, source: str = "ebay") -> Bargain:
    listing = _listing(title, listing_price, source)
    discount = 1.0 - (listing_price / market_price)
    return Bargain(
        listing=listing,
        market_price=market_price,
        discount_pct=discount,
        price_source="price_guide",
    )


class TestSplitMessage:
    def test_short_message_returned_as_single_chunk(self):
        text = "Hello, Warhammer Scout!"
        assert _split_message(text) == [text]

    def test_exactly_max_length_is_single_chunk(self):
        text = "x" * 4096
        assert _split_message(text) == [text]

    def test_long_message_split_into_chunks(self):
        # Build a message that's definitely over 4096 chars
        line = "A" * 100 + "\n"
        text = line * 50  # 5100 chars
        chunks = _split_message(text)
        assert len(chunks) > 1
        # Each chunk must be within the limit
        for chunk in chunks:
            assert len(chunk) <= 4096

    def test_split_preserves_all_content(self):
        line = "Book title here\n"
        text = line * 50
        chunks = _split_message(text)
        reconstructed = "\n".join(chunks)
        # All original lines should be present
        for chunk in chunks:
            assert chunk.strip()

    def test_split_breaks_on_newline(self):
        # Content that would split mid-line if not careful
        first_block = "A\n" * 40   # ~80 chars
        second_block = "B\n" * 40
        text = first_block + "X" * 4000 + "\n" + second_block
        chunks = _split_message(text)
        # Should not split in the middle of "X" * 4000 if there's a newline after it
        for chunk in chunks:
            assert len(chunk) <= 4096


class TestFormatBargains:
    def test_header_shows_count(self):
        bargains = [_bargain("Horus Rising Hardback", 15.0, 30.0)]
        text = format_bargains(bargains)
        assert "1 bargain" in text

    def test_plural_count(self):
        bargains = [
            _bargain("Horus Rising Hardback", 15.0, 30.0),
            _bargain("Betrayer Hardback", 20.0, 40.0),
        ]
        text = format_bargains(bargains)
        assert "2 bargain" in text

    def test_contains_title(self):
        bargains = [_bargain("Horus Rising Hardback", 15.0, 30.0)]
        assert "Horus Rising Hardback" in format_bargains(bargains)

    def test_contains_prices(self):
        bargains = [_bargain("Horus Rising Hardback", 15.0, 30.0)]
        text = format_bargains(bargains)
        assert "15.00" in text
        assert "30.00" in text

    def test_contains_url(self):
        bargains = [_bargain("Horus Rising Hardback", 15.0, 30.0)]
        assert "https://ebay.co.uk/itm/1" in format_bargains(bargains)

    def test_source_label_ebay(self):
        bargains = [_bargain("Horus Rising Hardback", 15.0, 30.0, source="ebay")]
        assert "eBay" in format_bargains(bargains)

    def test_source_label_vinted(self):
        bargains = [_bargain("Horus Rising Hardback", 15.0, 30.0, source="vinted")]
        assert "Vinted" in format_bargains(bargains)

    def test_discount_percentage_shown(self):
        bargains = [_bargain("Horus Rising Hardback", 15.0, 30.0)]
        text = format_bargains(bargains)
        assert "50%" in text


class TestFormatBundles:
    def test_header_shows_count(self):
        bundles = [_listing("Warhammer bundle x5", 20.0)]
        text = format_bundles(bundles)
        assert "1 bundle" in text

    def test_contains_title_and_price(self):
        bundles = [_listing("Warhammer bundle x5", 20.0)]
        text = format_bundles(bundles)
        assert "Warhammer bundle x5" in text
        assert "20.00" in text

    def test_contains_url(self):
        bundles = [_listing("Bundle", 10.0, url="https://vinted.co.uk/items/99")]
        assert "https://vinted.co.uk/items/99" in format_bundles(bundles)
