"""Tests for sources/reddit.py — RSS parsing and signal detection."""
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from sources.reddit import _parse_feed, _sanitize_xml, fetch_signals


# --- XML helpers ---

def _atom_feed(entries: list[dict]) -> str:
    entries_xml = ""
    for e in entries:
        entries_xml += f"""
  <entry>
    <title>{e.get("title", "")}</title>
    <link href="{e.get("url", "https://reddit.com/r/test/comments/abc/")}"/>
    <published>{e.get("published", "2026-04-20T10:00:00+00:00")}</published>
    <content type="html">{e.get("body", "")}</content>
  </entry>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test</title>{entries_xml}
</feed>"""


def _rss_feed(items: list[dict]) -> str:
    items_xml = ""
    for item in items:
        items_xml += f"""
    <item>
      <title>{item.get("title", "")}</title>
      <link>{item.get("url", "https://example.com/article")}</link>
      <pubDate>{item.get("pubDate", "Sun, 20 Apr 2026 10:00:00 +0000")}</pubDate>
      <description>{item.get("body", "")}</description>
    </item>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>{items_xml}
  </channel>
</rss>"""


def _recent_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _old_iso(days: int = 10) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _mock_client(responses: dict[str, str]):
    """responses: {url_fragment: xml_text}"""
    mock = MagicMock()

    def get_side_effect(url, **kwargs):
        for fragment, xml in responses.items():
            if fragment in url:
                resp = MagicMock()
                resp.text = xml
                resp.raise_for_status = MagicMock()
                return resp
        raise ValueError(f"Unexpected URL: {url}")

    mock.get.side_effect = get_side_effect
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


# --- _parse_feed unit tests ---

class TestParseFeed:
    def test_parses_atom_entries(self):
        xml = _atom_feed([{"title": "Test Post", "url": "https://reddit.com/r/fantasy/comments/abc/"}])
        items = _parse_feed(xml)
        assert len(items) == 1
        assert items[0]["title"] == "Test Post"
        assert "reddit.com" in items[0]["url"]

    def test_parses_rss_items(self):
        xml = _rss_feed([{"title": "Publisher News", "url": "https://example.com/news"}])
        items = _parse_feed(xml)
        assert len(items) == 1
        assert items[0]["title"] == "Publisher News"
        assert items[0]["url"] == "https://example.com/news"

    def test_returns_empty_on_invalid_xml(self):
        assert _parse_feed("not xml at all {{{{") == []

    def test_html_entities_in_feed_content_do_not_cause_parse_error(self):
        # &nbsp; and &mdash; are valid HTML but undefined in XML without DOCTYPE.
        # They must be escaped to &amp;nbsp; etc. so ET.fromstring doesn't raise.
        xml = _rss_feed([{"title": "New &amp; limited&nbsp;edition &mdash; sold out",
                          "pubDate": "Sun, 20 Apr 2026 10:00:00 +0000"}])
        # Inject raw entities into the XML string (bypassing our helper's escaping)
        raw_xml = xml.replace("&amp;nbsp;", "&nbsp;").replace("&amp;mdash;", "&mdash;")
        items = _parse_feed(raw_xml)
        assert len(items) == 1

    def test_sanitize_xml_escapes_html_entities(self):
        assert "&amp;nbsp;" in _sanitize_xml("hello&nbsp;world")
        assert "&amp;mdash;" in _sanitize_xml("one&mdash;two")

    def test_sanitize_xml_preserves_valid_xml_entities(self):
        # &amp; &lt; &gt; &quot; &apos; must not be double-escaped
        assert _sanitize_xml("&amp;") == "&amp;"
        assert _sanitize_xml("&lt;b&gt;") == "&lt;b&gt;"

    def test_sanitize_xml_escapes_bare_ampersand_in_url(self):
        # &utm_source= is a bare & that should become &amp;utm_source=
        assert "&amp;utm_source=" in _sanitize_xml("https://example.com?a=1&utm_source=rss")

    def test_atom_published_timestamp_parsed(self):
        xml = _atom_feed([{"title": "x", "published": "2026-04-20T10:00:00+00:00"}])
        items = _parse_feed(xml)
        assert items[0]["published_ts"] > 0

    def test_rss_pubdate_parsed(self):
        xml = _rss_feed([{"title": "x", "pubDate": "Sun, 20 Apr 2026 10:00:00 +0000"}])
        items = _parse_feed(xml)
        assert items[0]["published_ts"] > 0

    def test_multiple_entries_returned(self):
        xml = _atom_feed([{"title": "A"}, {"title": "B"}, {"title": "C"}])
        items = _parse_feed(xml)
        assert len(items) == 3


# --- fetch_signals integration tests ---

class TestSignalDetection:
    def test_adaptation_signal_reddit(self):
        xml = _atom_feed([{"title": "Joe Abercrombie TV series announced", "published": _recent_iso()}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [])
        assert len(signals) == 1
        assert "adaptation" in signals[0]["signal_types"]

    def test_scarcity_signal_publisher_feed(self):
        xml = _rss_feed([{"title": "Sanderson limited edition sold out", "pubDate": "Sun, 20 Apr 2026 10:00:00 +0000"}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"orbitbooks": xml})):
            signals = fetch_signals([], [("Orbit Books", "https://orbitbooks.net/feed/")])
        assert len(signals) == 1
        assert "scarcity" in signals[0]["signal_types"]

    def test_award_signal_detected(self):
        xml = _atom_feed([{"title": "Abercrombie wins Hugo Award", "published": _recent_iso()}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [])
        assert "award" in signals[0]["signal_types"]

    def test_author_news_signal_detected(self):
        xml = _atom_feed([{"title": "Terry Pratchett posthumous novel announced", "published": _recent_iso()}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [])
        assert "author_news" in signals[0]["signal_types"]

    def test_multiple_signal_types_on_one_post(self):
        xml = _atom_feed([{"title": "Sanderson Hugo winner — new edition sold out", "published": _recent_iso()}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [])
        types = signals[0]["signal_types"]
        assert "award" in types
        assert "scarcity" in types


class TestAuthorFilter:
    def test_reddit_post_without_author_excluded(self):
        xml = _atom_feed([{"title": "Amazing TV series announced for random book", "published": _recent_iso()}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [])
        assert signals == []

    def test_publisher_feed_skips_author_filter(self):
        # No known author mentioned — should still be detected from a publisher feed
        xml = _rss_feed([{"title": "New limited edition sold out already", "pubDate": "Sun, 20 Apr 2026 10:00:00 +0000"}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"gollancz": xml})):
            signals = fetch_signals([], [("Gollancz", "https://gollancz.co.uk/feed/")])
        assert len(signals) == 1

    def test_warhammer_keyword_matches_author_filter(self):
        xml = _atom_feed([{"title": "Warhammer Black Library limited edition announced", "published": _recent_iso()}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/warhammer40k/": xml})):
            signals = fetch_signals(["warhammer40k"], [])
        assert len(signals) == 1

    def test_author_in_body_matches(self):
        xml = _atom_feed([{
            "title": "Great news this week",
            "body": "Brandon Sanderson signed edition sold out",
            "published": _recent_iso(),
        }])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [])
        assert len(signals) == 1


class TestTimeCutoff:
    def test_old_post_excluded(self):
        xml = _atom_feed([{"title": "Abercrombie TV series announced", "published": _old_iso(8)}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [], days=7)
        assert signals == []

    def test_recent_post_included(self):
        xml = _atom_feed([{"title": "Abercrombie TV series announced", "published": _recent_iso()}])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [], days=7)
        assert len(signals) == 1


class TestSortedNewestFirst:
    def test_results_sorted_by_age_ascending(self):
        now = datetime.now(timezone.utc)
        xml = _atom_feed([
            {"title": "Abercrombie TV adaptation announced",
             "published": (now - timedelta(hours=48)).isoformat()},
            {"title": "Sanderson Hugo Award winner",
             "published": (now - timedelta(hours=2)).isoformat()},
            {"title": "Black Library limited edition sold out",
             "published": (now - timedelta(hours=24)).isoformat()},
        ])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [])
        ages = [s["age_hours"] for s in signals]
        assert ages == sorted(ages)

    def test_signal_fields_present(self):
        xml = _atom_feed([{
            "title": "Abercrombie Netflix adaptation announced",
            "url": "https://reddit.com/r/fantasy/comments/abc/",
            "published": _recent_iso(),
        }])
        with patch("sources.reddit.httpx.Client", return_value=_mock_client({"/r/fantasy/": xml})):
            signals = fetch_signals(["fantasy"], [])
        s = signals[0]
        assert s["source"] == "r/fantasy"
        assert "adaptation" in s["signal_types"]
        assert "reddit.com" in s["url"]
        assert s["age_hours"] >= 0


class TestMultipleSources:
    def test_reddit_and_publisher_feeds_aggregated(self):
        reddit_xml = _atom_feed([{"title": "Abercrombie TV adaptation announced", "published": _recent_iso()}])
        publisher_xml = _rss_feed([{"title": "New reprint sold out", "pubDate": "Sun, 20 Apr 2026 10:00:00 +0000"}])
        responses = {"/r/fantasy/": reddit_xml, "gollancz": publisher_xml}
        with patch("sources.reddit.httpx.Client", return_value=_mock_client(responses)):
            signals = fetch_signals(["fantasy"], [("Gollancz", "https://gollancz.co.uk/feed/")])
        assert len(signals) == 2
        sources = {s["source"] for s in signals}
        assert "r/fantasy" in sources
        assert "Gollancz" in sources


class TestHTTPErrorHandling:
    def test_http_error_skips_subreddit_continues(self):
        import httpx

        good_xml = _atom_feed([{"title": "Sanderson Hugo Award winner", "published": _recent_iso()}])
        mock = MagicMock()

        def get_side_effect(url, **kwargs):
            if "/r/fantasy/" in url:
                bad = MagicMock()
                bad.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "403", request=MagicMock(), response=MagicMock(status_code=403)
                )
                return bad
            resp = MagicMock()
            resp.text = good_xml
            resp.raise_for_status = MagicMock()
            return resp

        mock.get.side_effect = get_side_effect
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=False)

        with patch("sources.reddit.httpx.Client", return_value=mock):
            signals = fetch_signals(["fantasy", "printSF"], [])

        assert len(signals) == 1

    def test_connection_error_returns_empty(self):
        import httpx

        mock = MagicMock()
        mock.get.side_effect = httpx.ConnectError("refused")
        mock.__enter__ = MagicMock(return_value=mock)
        mock.__exit__ = MagicMock(return_value=False)

        with patch("sources.reddit.httpx.Client", return_value=mock):
            signals = fetch_signals(["fantasy"], [])

        assert signals == []
