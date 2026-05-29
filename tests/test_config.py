"""Tests for config.py — validates search term integrity and the subscription box watchlist."""
import config


class TestSubscriptionBoxTerms:
    def test_cross_product_count(self):
        terms = config._subscription_box_terms()
        expected = len(config.SUBSCRIPTION_BOX_AUTHORS) * len(config.SUBSCRIPTION_BOXES)
        assert len(terms) == expected

    def test_term_format(self):
        for term, max_results in config._subscription_box_terms():
            assert isinstance(term, str) and term
            assert isinstance(max_results, int) and max_results > 0

    def test_all_authors_and_boxes_represented(self):
        terms = [t for t, _ in config._subscription_box_terms()]
        for author in config.SUBSCRIPTION_BOX_AUTHORS:
            for box in config.SUBSCRIPTION_BOXES:
                assert f"{author} {box}" in terms

    def test_custom_max_results(self):
        for _, max_results in config._subscription_box_terms(max_results=7):
            assert max_results == 7


class TestSearchTermIntegrity:
    """Ensure no accidental duplicate search terms across each list."""

    def _check_no_duplicates(self, terms: list[tuple[str, int]], list_name: str) -> None:
        seen: set[str] = set()
        dupes = []
        for term, _ in terms:
            if term in seen:
                dupes.append(term)
            seen.add(term)
        assert dupes == [], f"Duplicate terms in {list_name}: {dupes}"

    def test_fantasy_search_terms_no_duplicates(self):
        self._check_no_duplicates(config.FANTASY_SEARCH_TERMS, "FANTASY_SEARCH_TERMS")

    def test_fantasy_vinted_no_duplicates(self):
        self._check_no_duplicates(config.FANTASY_VINTED_SEARCH_TERMS, "FANTASY_VINTED_SEARCH_TERMS")

    def test_etsy_fantasy_no_duplicates(self):
        self._check_no_duplicates(config.ETSY_FANTASY_SEARCH_TERMS, "ETSY_FANTASY_SEARCH_TERMS")

    def test_depop_fantasy_no_duplicates(self):
        self._check_no_duplicates(config.DEPOP_FANTASY_SEARCH_TERMS, "DEPOP_FANTASY_SEARCH_TERMS")

    def test_all_search_term_lists_well_formed(self):
        all_lists = [
            ("SEARCH_TERMS", config.SEARCH_TERMS),
            ("VINTED_SEARCH_TERMS", config.VINTED_SEARCH_TERMS),
            ("ETSY_SEARCH_TERMS", config.ETSY_SEARCH_TERMS),
            ("ETSY_FANTASY_SEARCH_TERMS", config.ETSY_FANTASY_SEARCH_TERMS),
            ("FANTASY_SEARCH_TERMS", config.FANTASY_SEARCH_TERMS),
            ("FANTASY_VINTED_SEARCH_TERMS", config.FANTASY_VINTED_SEARCH_TERMS),
            ("DEPOP_FANTASY_SEARCH_TERMS", config.DEPOP_FANTASY_SEARCH_TERMS),
        ]
        for name, terms in all_lists:
            for item in terms:
                assert isinstance(item, tuple) and len(item) == 2, f"Bad item in {name}: {item!r}"
                term, max_results = item
                assert isinstance(term, str) and term, f"Empty term in {name}"
                assert isinstance(max_results, int) and max_results > 0, f"Bad max_results in {name}: {item!r}"
