"""
News feed monitor — Reddit RSS and publisher/trade RSS feeds.

Fetches recent posts/articles and identifies market signals: adaptation news,
scarcity/reprint announcements, award wins, or author news that could affect
secondhand prices.

No authentication required — uses public RSS/Atom endpoints.
"""
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

log = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "WarhammmerScout/1.0 secondhand-book-market-monitor (personal use)"}
_ATOM_NS = "http://www.w3.org/2005/Atom"
# old.reddit.com serves RSS without the auth restrictions that www.reddit.com now enforces
_REDDIT_RSS = "https://old.reddit.com/r/{sub}/new.rss"

# Common HTML entities that appear in RSS feeds but are not valid XML without a DOCTYPE
_HTML_ENTITIES = {
    "&nbsp;": " ", "&mdash;": "—", "&ndash;": "–", "&lsquo;": "'",
    "&rsquo;": "'", "&ldquo;": "\u201c", "&rdquo;": "\u201d",
    "&hellip;": "…", "&amp;amp;": "&amp;",
}

_SIGNAL_RE: dict[str, re.Pattern] = {
    "adaptation": re.compile(
        r"\b(tv series|television|film|movie|adaptation|netflix|amazon prime|"
        r"hbo|disney\+?|apple tv|peacock|paramount\+?|streaming|announced|greenlit)\b",
        re.IGNORECASE,
    ),
    "scarcity": re.compile(
        r"\b(out of print|oop|reprint|new edition|limited edition|"
        r"signed edition|collector.?s edition|selling out|sold out)\b",
        re.IGNORECASE,
    ),
    "award": re.compile(
        r"\b(hugo award|nebula award|world fantasy award|booker prize|"
        r"arthur c\.? clarke award|locus award|british fantasy award|"
        r"hugo winner|nebula winner|award winner)\b",
        re.IGNORECASE,
    ),
    "author_news": re.compile(
        r"\b(died|passed away|death of|in memoriam|final book|last novel|"
        r"posthumous|new book announced|new novel|sequel announced|"
        r"contract announced)\b",
        re.IGNORECASE,
    ),
}

# Reddit posts must mention a known author/publisher — publisher feeds are trusted without this
_AUTHOR_RE = re.compile(
    r"\b(abercrombie|sanderson|rothfuss|erikson|hobb|pratchett|gaiman|"
    r"iain\s+(?:m\.?\s+)?banks|peter\s+(?:f\.?\s+)?hamilton|alastair reynolds|richard morgan|"
    r"mark lawrence|gene wolfe|le guin|tolkien|jordan|george martin|"
    r"brent weeks|scott lynch|sullivan|r\.?\s*f\.?\s*kuang|clive barker|"
    r"glen cook|black library|horus heresy|warhammer|gollancz|orbit books|"
    r"tor books|subterranean press)\b",
    re.IGNORECASE,
)


def _parse_date(s: str) -> float:
    """Parse ISO 8601 or RFC 2822 date string to Unix timestamp."""
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(s).timestamp()
    except Exception:
        log.debug(f"Unparseable date string: {s!r} — skipping item")
        return 0.0  # treat as epoch so the item is always filtered out by cutoff


def _sanitize_xml(xml_text: str) -> str:
    """Replace common HTML entities that are invalid in XML without a DOCTYPE."""
    for entity, replacement in _HTML_ENTITIES.items():
        xml_text = xml_text.replace(entity, replacement)
    return xml_text


def _parse_feed(xml_text: str) -> list[dict]:
    """
    Parse RSS 2.0 or Atom XML into list of {title, url, published_ts, text}.
    Returns empty list on parse error.
    """
    try:
        root = ET.fromstring(_sanitize_xml(xml_text))
    except ET.ParseError as e:
        log.warning(f"XML parse error: {e}")
        return []

    if _ATOM_NS in root.tag:
        ns = {"a": _ATOM_NS}
        items = []
        for entry in root.findall("a:entry", ns):
            title_el = entry.find("a:title", ns)
            link_el = entry.find("a:link", ns)
            pub_el = entry.find("a:published", ns)
            if pub_el is None:
                pub_el = entry.find("a:updated", ns)
            content_el = entry.find("a:content", ns)
            if content_el is None:
                content_el = entry.find("a:summary", ns)
            # ET renders child HTML nodes as tail text; fall back to itertext for HTML content
            text = "".join(content_el.itertext()) if content_el is not None else ""
            items.append({
                "title": (title_el.text or "").strip() if title_el is not None else "",
                "url": link_el.get("href", "") if link_el is not None else "",
                "published_ts": _parse_date(pub_el.text or "") if pub_el is not None else time.time(),
                "text": text,
            })
        return items

    # RSS 2.0
    items = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")
        desc_el = item.find("description")
        items.append({
            "title": (title_el.text or "").strip() if title_el is not None else "",
            "url": (link_el.text or "").strip() if link_el is not None else "",
            "published_ts": _parse_date(pub_el.text or "") if pub_el is not None else time.time(),
            "text": desc_el.text or "" if desc_el is not None else "",
        })
    return items


def _score_items(items: list[dict], source: str, cutoff: float, author_filter: bool) -> list[dict]:
    signals = []
    for item in items:
        if item["published_ts"] < cutoff:
            continue
        full_text = f"{item['title']} {item['text'][:500]}"
        if author_filter and not _AUTHOR_RE.search(full_text):
            continue
        signal_types = [sig for sig, pat in _SIGNAL_RE.items() if pat.search(full_text)]
        if not signal_types:
            continue
        signals.append({
            "source": source,
            "title": item["title"],
            "url": item["url"],
            "signal_types": signal_types,
            "age_hours": round((time.time() - item["published_ts"]) / 3600, 1),
        })
    return signals


def fetch_signals(
    subreddits: list[str],
    feeds: list[tuple[str, str]],
    days: int = 7,
) -> list[dict]:
    """
    Fetch market signals from Reddit RSS and publisher/trade RSS feeds.

    subreddits: list of subreddit names (e.g. ["fantasy", "printSF"])
    feeds: list of (display_name, url) pairs for publisher/trade feeds
    days: look-back window

    Returns list of signal dicts sorted newest-first, each containing:
      source, title, url, signal_types (list), age_hours
    """
    signals: list[dict] = []
    cutoff = time.time() - (days * 86_400)

    # Reddit sets session cookies that trigger rate-limiting on subsequent requests
    # within the same connection — use a fresh client per subreddit to avoid this.
    for sub in subreddits:
        url = _REDDIT_RSS.format(sub=sub)
        try:
            with httpx.Client(timeout=15, headers=_HEADERS, follow_redirects=True) as client:
                resp = client.get(url)
            resp.raise_for_status()
            items = _parse_feed(resp.text)
            found = _score_items(items, f"r/{sub}", cutoff, author_filter=True)
            signals.extend(found)
            log.debug(f"r/{sub}: {len(items)} entries, {len(found)} signals")
        except httpx.HTTPStatusError as e:
            log.warning(f"Reddit RSS: HTTP {e.response.status_code} for r/{sub}")
        except httpx.HTTPError as e:
            log.warning(f"Reddit RSS: connection error for r/{sub} — {e}")

    with httpx.Client(timeout=15, headers=_HEADERS, follow_redirects=True) as client:
        for feed_name, feed_url in feeds:
            try:
                resp = client.get(feed_url)
                resp.raise_for_status()
                items = _parse_feed(resp.text)
                # Publisher feeds are on-topic by definition — no author filter needed
                found = _score_items(items, feed_name, cutoff, author_filter=False)
                signals.extend(found)
                log.debug(f"{feed_name}: {len(items)} entries, {len(found)} signals")
            except httpx.HTTPStatusError as e:
                log.warning(f"Feed '{feed_name}': HTTP {e.response.status_code}")
            except httpx.HTTPError as e:
                log.warning(f"Feed '{feed_name}': connection error — {e}")

    signals.sort(key=lambda x: x["age_hours"])
    log.info(
        f"News feeds: {len(signals)} signal(s) from "
        f"{len(subreddits)} subreddit(s) + {len(feeds)} publisher feed(s)"
    )
    return signals
