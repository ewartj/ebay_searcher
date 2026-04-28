"""Tests for scripts/market_scout.py."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import anthropic
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from market_scout import _opportunity_score, run_market_scout


# ---------------------------------------------------------------------------
# _opportunity_score
# ---------------------------------------------------------------------------

class TestOpportunityScore:
    def test_zero_median_returns_zero(self):
        assert _opportunity_score({"median": 0, "max": 50, "min": 10, "count": 5}) == 0.0

    def test_negative_median_returns_zero(self):
        assert _opportunity_score({"median": -1, "max": 50, "min": 10, "count": 5}) == 0.0

    def test_max_less_than_min_returns_zero(self):
        assert _opportunity_score({"median": 20, "max": 5, "min": 10, "count": 5}) == 0.0

    def test_missing_keys_returns_zero(self):
        assert _opportunity_score({}) == 0.0

    def test_single_listing_low_liquidity(self):
        score = _opportunity_score({"median": 20, "max": 30, "min": 10, "count": 1})
        assert score > 0
        assert score < _opportunity_score({"median": 20, "max": 30, "min": 10, "count": 20})

    def test_high_spread_scores_higher_than_low_spread(self):
        high = _opportunity_score({"median": 20, "max": 60, "min": 10, "count": 20})
        low  = _opportunity_score({"median": 20, "max": 25, "min": 15, "count": 20})
        assert high > low

    def test_liquidity_capped_at_20_listings(self):
        at_20  = _opportunity_score({"median": 20, "max": 40, "min": 10, "count": 20})
        at_100 = _opportunity_score({"median": 20, "max": 40, "min": 10, "count": 100})
        assert at_20 == pytest.approx(at_100)


# ---------------------------------------------------------------------------
# run_market_scout
# ---------------------------------------------------------------------------

def _make_claude_mock(text: str) -> MagicMock:
    mock = MagicMock()
    block = MagicMock(spec=anthropic.types.TextBlock)
    block.text = text
    mock.messages.create.return_value = MagicMock(content=[block])
    return mock


class TestRunMarketScout:
    def test_dry_run_prints_report(self, capsys):
        stats = {"median": 30.0, "min": 10.0, "max": 60.0, "count": 15}
        with patch("market_scout.fetch_market_stats", return_value={"subterranean press horror hardback": stats}), \
             patch("market_scout.anthropic.Anthropic", return_value=_make_claude_mock("STRONG: test niche")), \
             patch("market_scout.config.NICHE_SCOUT_TERMS", [("subterranean press horror hardback", "Sub Press")]):
            result = run_market_scout(dry_run=True)
        assert result == 0
        captured = capsys.readouterr()
        assert "STRONG: test niche" in captured.out

    def test_no_ebay_data_returns_0(self):
        with patch("market_scout.fetch_market_stats", return_value={}), \
             patch("market_scout.config.NICHE_SCOUT_TERMS", [("some term", "Some Niche")]):
            result = run_market_scout(dry_run=True)
        assert result == 0

    def test_empty_terms_returns_0(self):
        with patch("market_scout.config.NICHE_SCOUT_TERMS", []):
            result = run_market_scout(dry_run=True)
        assert result == 0

    def test_non_textblock_response_uses_fallback(self, capsys):
        mock_client = MagicMock()
        non_text_block = MagicMock()  # not a TextBlock instance
        del non_text_block.text
        mock_client.messages.create.return_value = MagicMock(content=[non_text_block])

        stats = {"median": 30.0, "min": 10.0, "max": 60.0, "count": 15}
        with patch("market_scout.fetch_market_stats", return_value={"term": stats}), \
             patch("market_scout.anthropic.Anthropic", return_value=mock_client), \
             patch("market_scout.config.NICHE_SCOUT_TERMS", [("term", "Label")]):
            result = run_market_scout(dry_run=True)
        assert result == 0
        assert "(No report generated)" in capsys.readouterr().out

    def test_empty_content_uses_fallback(self, capsys):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(content=[])

        stats = {"median": 30.0, "min": 10.0, "max": 60.0, "count": 15}
        with patch("market_scout.fetch_market_stats", return_value={"term": stats}), \
             patch("market_scout.anthropic.Anthropic", return_value=mock_client), \
             patch("market_scout.config.NICHE_SCOUT_TERMS", [("term", "Label")]):
            result = run_market_scout(dry_run=True)
        assert result == 0
        assert "(No report generated)" in capsys.readouterr().out
