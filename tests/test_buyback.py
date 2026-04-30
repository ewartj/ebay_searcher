"""Tests for sources/buyback.py."""
from unittest.mock import MagicMock, patch

import pytest

from models import Bargain, Listing
from sources.buyback import enrich_bargains, extract_isbn


def _listing(title: str = "Some Book", isbn: str | None = None) -> Listing:
    return Listing(title=title, price_gbp=10.0, url="https://example.com", source="ebay", isbn=isbn)


def _bargain(title: str = "Some Book", isbn: str | None = None) -> Bargain:
    return Bargain(
        listing=_listing(title, isbn=isbn),
        market_price=30.0,
        discount_pct=0.67,
        price_source="price_guide",
    )


# --- extract_isbn ---

class TestExtractIsbn:
    def test_extracts_isbn13(self):
        assert extract_isbn("Horus Rising 9780241241851 Hardback") == "9780241241851"

    def test_extracts_isbn10(self):
        assert extract_isbn("Book title 019853556X signed") == "019853556X"

    def test_prefers_isbn13_over_isbn10(self):
        result = extract_isbn("9780241241851 and 019853556X")
        assert result == "9780241241851"

    def test_returns_none_when_no_isbn(self):
        assert extract_isbn("Horus Rising Hardback Signed") is None

    def test_returns_none_for_empty_string(self):
        assert extract_isbn("") is None

    def test_handles_isbn_at_start(self):
        assert extract_isbn("9780241241851 — The Name of the Wind") == "9780241241851"

    def test_handles_isbn_at_end(self):
        assert extract_isbn("The Name of the Wind 9780241241851") == "9780241241851"


# --- enrich_bargains ---

class TestEnrichBargains:
    def test_no_op_for_empty_list(self):
        enrich_bargains([])  # should not raise

    def test_skips_bargains_without_isbn_in_title(self):
        bargain = _bargain("Horus Rising Hardback Signed")
        enrich_bargains([bargain])
        assert bargain.buyback_floor is None

    def test_sets_buyback_floor_when_isbn_found_and_price_returned(self):
        bargain = _bargain("Horus Rising 9780241241851 Hardback")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"price": 3.50}

        with patch("sources.buyback.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.return_value = mock_resp
            enrich_bargains([bargain])

        assert bargain.buyback_floor == pytest.approx(3.50)

    def test_leaves_floor_none_when_api_returns_no_price_key(self):
        bargain = _bargain("My Book 9780241241851")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}  # no recognised key

        with patch("sources.buyback.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.return_value = mock_resp
            enrich_bargains([bargain])

        assert bargain.buyback_floor is None

    def test_leaves_floor_none_on_http_error(self):
        import httpx
        bargain = _bargain("My Book 9780241241851")

        with patch("sources.buyback.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError("refused")
            enrich_bargains([bargain])

        assert bargain.buyback_floor is None

    def test_uses_listing_isbn_over_title_regex(self):
        # Title has no ISBN but listing.isbn is set (e.g. from eBay localizedAspects)
        bargain = _bargain("Horus Rising Hardback Signed", isbn="9780241241851")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"price": 4.00}

        with patch("sources.buyback.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.return_value = mock_resp
            enrich_bargains([bargain])

        assert bargain.buyback_floor == pytest.approx(4.00)

    def test_enriches_multiple_bargains_independently(self):
        b1 = _bargain("Book A 9780241241851")
        b2 = _bargain("Book B — no isbn")
        b3 = _bargain("Book C 9780747532699")

        call_count = 0

        def fake_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            isbn = kwargs.get("params", {}).get("barcode", "")
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"price": 2.0 * call_count}
            return resp

        with patch("sources.buyback.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.side_effect = fake_get
            enrich_bargains([b1, b2, b3])

        assert b1.buyback_floor == pytest.approx(2.0)
        assert b2.buyback_floor is None
        assert b3.buyback_floor == pytest.approx(4.0)
        assert call_count == 2  # only ISBNs trigger HTTP calls
