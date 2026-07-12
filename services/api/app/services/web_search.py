from __future__ import annotations

import html
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._field: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            if self._current and self._current["title"] and self._current["url"]:
                self.results.append(self._current)
            href = html.unescape(attributes.get("href") or "")
            query = parse_qs(urlparse(href).query).get("uddg")
            self._current = {"title": "", "url": unquote(query[0]) if query else href, "snippet": ""}
            self._field = "title"
        elif self._current and "result__snippet" in classes:
            self._field = "snippet"

    def handle_endtag(self, tag: str) -> None:
        if self._current and tag == "a" and self._field == "snippet":
            if self._current["title"] and self._current["url"]:
                self.results.append(self._current)
            self._current = None
            self._field = None
        elif self._current and tag == "a" and self._field == "title":
            self._field = None

    def handle_data(self, data: str) -> None:
        if self._current and self._field:
            self._current[self._field] += " ".join(data.split())


def search_public_web(query: str, *, limit: int = 5) -> list[dict[str, str]]:
    """Search public web results without coupling Snowy to a model vendor."""
    normalized = " ".join(query.split())[:300]
    if not normalized:
        return []
    request = Request(
        f"https://www.bing.com/search?q={quote_plus(normalized)}&format=rss",
        headers={"User-Agent": "AI-Research-Radar/0.1"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = response.read()
        root = ElementTree.fromstring(payload)
        results = []
        for item in root.findall(".//item")[:limit]:
            title = "".join(item.findtext("title", "").split())
            url = item.findtext("link", "").strip()
            snippet = " ".join(item.findtext("description", "").split())
            if title and url.startswith(("http://", "https://")):
                results.append({"title": title, "url": url, "snippet": snippet})
        if results:
            return results
    except Exception:
        pass

    # Keep DuckDuckGo as a fallback for environments where Bing RSS is blocked.
    request = Request(
        f"https://html.duckduckgo.com/html/?q={quote_plus(normalized)}",
        headers={"User-Agent": "AI-Research-Radar/0.1"},
        method="GET",
    )
    with urlopen(request, timeout=15) as response:
        payload = response.read().decode("utf-8", errors="ignore")
    parser = _DuckDuckGoParser()
    parser.feed(payload)
    if parser._current and parser._current["title"] and parser._current["url"]:
        parser.results.append(parser._current)
    unique: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in parser.results:
        url = item["url"]
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)
        unique.append({"title": item["title"].strip(), "url": url, "snippet": item["snippet"].strip()})
        if len(unique) >= limit:
            break
    return unique
