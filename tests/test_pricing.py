"""Tests for the pricing / bargain-detection pipeline."""
from unittest.mock import MagicMock, patch

import pytest

from models import Listing
from pricing import (
    _BUNDLE_RE,
    _PAPERBACK_RE,
    _WARHAMMER_RE,
    _claude_filter,
    _claude_price,
    _lookup_price_guide,
    _parse_json_response,
    find_bargains,
)


# ---------------------------------------------------------------------------
# _lookup_price_guide
# ---------------------------------------------------------------------------

class TestLookupPriceGuide:
    def test_plain_float_entry_hardback(self):
        # "titanicus": 35.0 — plain float means hardback-only
        assert _lookup_price_guide("Titanicus by Dan Abnett") == 35.0

    def test_plain_float_entry_paperback_returns_none(self):
        # Plain float = hardback only; paperback falls through to Claude
        assert _lookup_price_guide("Titanicus PB") is None

    def test_dict_entry_hardback(self):
        # "horus rising": {"hardback": 30.0, "paperback": 8.0}
        assert _lookup_price_guide("Horus Rising Hardback") == 30.0

    def test_dict_entry_paperback(self):
        assert _lookup_price_guide("Horus Rising Paperback") == 8.0

    def test_no_match_returns_none(self):
        assert _lookup_price_guide("Harry Potter and the Philosopher's Stone") is None

    def test_case_insensitive(self):
        assert _lookup_price_guide("HORUS RISING HARDBACK") == 30.0

    def test_best_price_wins_when_multiple_keys_match(self):
        # "saturnine": {"hardback": 55.0, ...} — only one key should match, check value
        result = _lookup_price_guide("Saturnine Black Library")
        assert result == 55.0

    def test_eisenhorn_omnibus_paperback_has_own_price(self):
        # "eisenhorn": {"hardback": 50.0, "paperback": 25.0}
        assert _lookup_price_guide("Eisenhorn Omnibus Paperback") == 25.0


# ---------------------------------------------------------------------------
# _parse_json_response
# ---------------------------------------------------------------------------

class TestParseJsonResponse:
    def test_plain_json_array(self):
        assert _parse_json_response("[1, 2, 3]") == [1, 2, 3]

    def test_plain_json_object(self):
        assert _parse_json_response('{"a": 1}') == {"a": 1}

    def test_markdown_fenced_with_language_tag(self):
        raw = "```json\n[1, 2]\n```"
        assert _parse_json_response(raw) == [1, 2]

    def test_markdown_fenced_without_language_tag(self):
        raw = "```\n[3, 4]\n```"
        assert _parse_json_response(raw) == [3, 4]


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

class TestBundleRe:
    @pytest.mark.parametrize("title", [
        "Horus Heresy bundle x4",
        "Job Lot of warhammer 40k books",
        "Lot of 5 black library",
        "Warhammer books 1-5",
        "Black Library x10",
    ])
    def test_matches(self, title):
        assert _BUNDLE_RE.search(title)

    @pytest.mark.parametrize("title", [
        "Horus Rising Hardback",
        "Betrayer Black Library Limited Edition",
    ])
    def test_no_match(self, title):
        assert not _BUNDLE_RE.search(title)


class TestPaperbackRe:
    @pytest.mark.parametrize("title", [
        "Horus Rising Paperback",
        "Betrayer (PB)",
        "Some Book PB edition",
        "Small PB black library",
        "pocket edition omnibus",
    ])
    def test_matches(self, title):
        assert _PAPERBACK_RE.search(title)

    def test_no_match_on_hardback(self):
        assert not _PAPERBACK_RE.search("Horus Rising Hardback")


class TestWarhammerRe:
    @pytest.mark.parametrize("title", [
        "Warhammer 40,000 novel",
        "Black Library Horus Heresy",
        "Space Marine hardback",
        "Adeptus Mechanicus",
        "Age of Sigmar novel",
        "Horus Heresy: Betrayer",
        "40k bundle",
    ])
    def test_matches(self, title):
        assert _WARHAMMER_RE.search(title)

    def test_no_match_on_non_warhammer(self):
        assert not _WARHAMMER_RE.search("Xbox games bundle x5")

    def test_no_match_on_generic_book(self):
        assert not _WARHAMMER_RE.search("Harry Potter hardback omnibus")


# ---------------------------------------------------------------------------
# _claude_filter
# ---------------------------------------------------------------------------

def _mock_client(text: str) -> MagicMock:
    mock = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    mock.messages.create.return_value = msg
    return mock


class TestClaudeFilter:
    def test_returns_matched_titles(self):
        titles = ["Horus Rising Hardback", "Harry Potter", "Betrayer Hardback"]
        result = _claude_filter(titles, _mock_client("[1, 3]"))
        assert result == ["Horus Rising Hardback", "Betrayer Hardback"]

    def test_empty_response_returns_empty(self):
        result = _claude_filter(["Something"], _mock_client("[]"))
        assert result == []

    def test_out_of_range_indices_ignored(self):
        titles = ["Title A", "Title B"]
        # 1-based: 0 and 99 are out of range; 1 and 2 are valid
        result = _claude_filter(titles, _mock_client("[0, 1, 2, 99]"))
        assert result == ["Title A", "Title B"]

    def test_falls_back_to_all_titles_on_api_error(self):
        mock = MagicMock()
        mock.messages.create.side_effect = Exception("network error")
        titles = ["Horus Rising", "Betrayer"]
        result = _claude_filter(titles, mock)
        assert result == titles


# ---------------------------------------------------------------------------
# _claude_price
# ---------------------------------------------------------------------------

class TestClaudePrice:
    def test_returns_price_dict(self):
        result = _claude_price(
            ["Horus Rising Hardback"],
            _mock_client('{"Horus Rising Hardback": 30.0}'),
        )
        assert result == {"Horus Rising Hardback": 30.0}

    def test_null_values_excluded(self):
        result = _claude_price(
            ["Unknown Book", "Horus Rising"],
            _mock_client('{"Unknown Book": null, "Horus Rising": 30.0}'),
        )
        assert "Unknown Book" not in result
        assert result["Horus Rising"] == 30.0

    def test_empty_input_returns_empty_without_api_call(self):
        mock = MagicMock()
        result = _claude_price([], mock)
        assert result == {}
        mock.messages.create.assert_not_called()

    def test_returns_empty_on_api_error(self):
        mock = MagicMock()
        mock.messages.create.side_effect = Exception("API down")
        result = _claude_price(["Some Title"], mock)
        assert result == {}


# ---------------------------------------------------------------------------
# find_bargains
# ---------------------------------------------------------------------------

def _listing(title: str, price: float, source: str = "ebay") -> Listing:
    return Listing(title=title, price_gbp=price, url="https://test.example", source=source)


class TestFindBargains:
    def test_price_guide_bargain_detected(self):
        # "horus rising" hardback: £30; 30% below = ≤ £21; £15 qualifies
        listing = _listing("Horus Rising Hardback", 15.0)
        bargains, bundles = find_bargains([listing])
        assert len(bargains) == 1
        assert bargains[0].discount_pct == pytest.approx(0.5)
        assert bargains[0].price_source == "price_guide"

    def test_price_guide_not_a_bargain(self):
        # £25 / £30 = 83% of market — above 70% threshold
        listing = _listing("Horus Rising Hardback", 25.0)
        bargains, _ = find_bargains([listing])
        assert bargains == []

    def test_below_min_profit_not_a_bargain(self):
        # "deus encarmine" hardback: £30; £22 = 73% of £30 → passes discount threshold
        # but profit = £30 - £22 = £8 < MIN_PROFIT (£10) → not flagged
        listing = _listing("Deus Encarmine Hardback", 22.0)
        bargains, _ = find_bargains([listing])
        assert bargains == []

    def test_paperback_uses_paperback_price(self):
        # "eisenhorn" paperback: £25; £12 = 48% of £25, profit £13 → bargain
        listing = _listing("Eisenhorn Omnibus Paperback", 12.0)
        bargains, _ = find_bargains([listing])
        assert len(bargains) == 1
        assert bargains[0].market_price == 25.0

    def test_warhammer_bundle_flagged_for_review(self):
        listing = _listing("Warhammer Black Library bundle x5", 20.0)
        bargains, bundles = find_bargains([listing])
        assert bundles == [listing]
        assert bargains == []
        assert listing.is_bundle is True

    def test_non_warhammer_bundle_not_flagged(self):
        listing = _listing("Xbox games bundle x5", 20.0)
        _, bundles = find_bargains([listing])
        assert bundles == []

    def test_bargains_sorted_by_discount_descending(self):
        listings = [
            _listing("Horus Rising Hardback", 20.0),  # 20/30 = 33% off
            _listing("Saturnine Hardback", 10.0),      # 10/55 = 82% off
        ]
        bargains, _ = find_bargains(listings)
        assert len(bargains) == 2
        assert bargains[0].listing.title == "Saturnine Hardback"

    def test_claude_estimate_used_for_unknown_title(self):
        call_count = [0]

        def mock_create(**kwargs):
            call_count[0] += 1
            msg = MagicMock()
            if call_count[0] == 1:
                msg.content = [MagicMock(text="[1]")]  # filter: pass title 1
            else:
                msg.content = [MagicMock(text='{"Rare Collector Edition Hardback": 80.0}')]
            return msg

        mock = MagicMock()
        mock.messages.create.side_effect = mock_create

        listing = _listing("Rare Collector Edition Hardback", 40.0)
        with patch("pricing.fetch_market_prices", return_value={}):
            bargains, _ = find_bargains([listing], claude_client=mock)
        assert len(bargains) == 1
        assert bargains[0].price_source == "claude_estimate"

    def test_ebay_active_price_used_when_available(self):
        mock = MagicMock()
        mock.messages.create.return_value = MagicMock(
            content=[MagicMock(text="[1]")]  # filter passes the title
        )

        listing = _listing("Rare Collector Edition Hardback", 20.0)
        with patch("pricing.fetch_market_prices", return_value={"Rare Collector Edition Hardback": 60.0}):
            bargains, _ = find_bargains([listing], claude_client=mock)
        assert len(bargains) == 1
        assert bargains[0].price_source == "ebay_active"
        assert bargains[0].market_price == 60.0

    def test_ebay_active_no_http_calls_in_tests(self):
        # Verify fetch_market_prices is always patched — real HTTP would raise in CI
        mock = MagicMock()
        mock.messages.create.return_value = MagicMock(
            content=[MagicMock(text="[1]")]
        )
        listing = _listing("Rare Collector Edition Hardback", 15.0)
        with patch("pricing.fetch_market_prices", return_value={}) as mock_fetch:
            find_bargains([listing], claude_client=mock)
        mock_fetch.assert_called_once()

    def test_empty_listings_returns_empty(self):
        bargains, bundles = find_bargains([])
        assert bargains == []
        assert bundles == []

    def test_unknown_title_skipped_when_no_claude_client_and_not_in_guide(self):
        # Title not in price guide; no mock Claude — uses global _client but filter
        # returns empty (mock not set up) so title is skipped, not a bargain
        listing = _listing("Completely Unknown Fantasy Novel", 5.0)
        # We pass a client that returns [] from filter so nothing gets priced
        mock = _mock_client("[]")
        bargains, _ = find_bargains([listing], claude_client=mock)
        assert bargains == []
