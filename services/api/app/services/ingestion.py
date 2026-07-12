from __future__ import annotations

import hashlib
import html
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, Source, utc_now

Fetcher = Callable[[str], tuple[bytes, str]]


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: list[str] = []
        self.text: list[str] = []
        self.authors: list[str] = []
        self.published: str | None = None
        self.canonical_url: str | None = None
        self._active_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "meta":
            key = attributes.get("name") or attributes.get("property")
            value = attributes.get("content")
            if key in {"author", "article:author", "citation_author"} and value:
                self.authors.append(value)
            if key in {"article:published_time", "citation_publication_date", "date"} and value:
                self.published = value
            if key == "og:url" and value:
                self.canonical_url = value.strip()
        if tag == "link" and "canonical" in (attributes.get("rel") or "").lower() and attributes.get("href"):
            self.canonical_url = str(attributes["href"]).strip()
        if tag in {"title", "h1", "h2", "h3", "p", "li"}:
            self._active_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == self._active_tag:
            self._active_tag = None

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value:
            return
        if self._active_tag == "title":
            self.title.append(value)
        elif self._active_tag in {"h1", "h2", "h3", "p", "li"}:
            self.text.append(value)


class _MarkupTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def clean_markup(value: str) -> str:
    parser = _MarkupTextParser()
    parser.feed(html.unescape(value))
    return " ".join(parser.parts).strip()


def _parse_html(payload: bytes, source_url: str) -> list[dict[str, object]]:
    parser = _PageParser()
    parser.feed(payload.decode("utf-8", errors="ignore"))
    title = html.unescape(" ".join(parser.title)).strip() or source_url
    if " - Intel Newsroom" in title:
        title = title.split(" - Intel Newsroom", 1)[0].strip()
    if " | " in title:
        title = title.split(" | ", 1)[0].strip()
    content = html.unescape("\n".join(dict.fromkeys(parser.text)))
    authors = list(dict.fromkeys(part.strip() for value in parser.authors for part in value.split(",") if part.strip()))
    return [{"title": title, "url": parser.canonical_url or source_url, "content": content or "暂无网页正文，请打开原文查看完整内容。", "content_level": "full_text" if content else "metadata", "published_at": _parse_datetime(parser.published), "authors": authors}]


def fetch_url(url: str, extra_headers: dict[str, str] | None = None, *, timeout: int | None = None) -> tuple[bytes, str]:
    headers = {"User-Agent": "AI-Research-Radar/0.1"}
    headers.update(extra_headers or {})
    request = Request(url, headers=headers)
    request_timeout = timeout or settings.source_request_timeout_seconds
    for attempt in range(3):
        try:
            with urlopen(request, timeout=request_timeout) as response:
                return response.read(), response.headers.get_content_type()
        except HTTPError as error:
            # Rate limits and transient upstream failures should be isolated to
            # the source. Retry briefly when the provider explicitly permits
            # it, then surface a useful error instead of an empty HTTPError.
            if error.code in {429, 500, 502, 503, 504} and attempt < 2:
                retry_after = error.headers.get("Retry-After") if error.headers else None
                try:
                    delay = min(2.0, max(0.25, float(retry_after or 0.5)))
                except (TypeError, ValueError):
                    delay = 0.5
                time.sleep(delay)
                continue
            raise RuntimeError(f"HTTP {error.code} from {urlparse(url).netloc or 'source'}") from error
        except (URLError, TimeoutError):
            if attempt == 1:
                raise
            time.sleep(0.35)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None


def _text(element: ElementTree.Element | None) -> str:
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def _parse_xml(payload: bytes) -> list[dict[str, object]]:
    root = ElementTree.fromstring(payload)
    entries = [element for element in root.iter() if _local_name(element.tag) in {"entry", "item"}]
    documents = []
    for entry in entries:
        fields = {_local_name(child.tag): child for child in entry}
        title = html.unescape(_text(fields.get("title")))
        link_element = fields.get("link")
        href = link_element.attrib.get("href") if link_element is not None else None
        url = href or (_text(link_element) if link_element is not None else "") or _text(fields.get("id"))
        content_element = next((fields.get(name) for name in ("summary", "description", "content") if fields.get(name) is not None), None)
        published_element = next((fields.get(name) for name in ("published", "updated", "pubDate") if fields.get(name) is not None), None)
        summary = clean_markup(_text(content_element))
        published = _text(published_element)
        authors = [_text(child) for child in entry if _local_name(child.tag) == "author" and _text(child)]
        if title and url:
            documents.append({"title": title, "url": url, "content": summary or "暂无摘要，请打开原文查看完整内容。", "content_level": "abstract" if summary else "metadata", "published_at": _parse_datetime(published), "authors": authors})
    return documents


def _parse_json(payload: bytes) -> list[dict[str, object]]:
    data = json.loads(payload.decode("utf-8"))
    items = data.get("message", {}).get("items", []) if isinstance(data, dict) else []
    documents = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        title = title[0] if isinstance(title, list) and title else title
        url = item.get("URL") or item.get("url")
        abstract = item.get("abstract")
        published_parts = item.get("published", {}).get("date-parts", [])
        published = None
        if published_parts and published_parts[0]:
            parts = published_parts[0]
            published = datetime(*([int(part) for part in parts] + [1] * (3 - len(parts))), tzinfo=timezone.utc)
        if title and url:
            authors = []
            for author in item.get("author", []) if isinstance(item.get("author", []), list) else []:
                if isinstance(author, dict):
                    full_name = " ".join(str(part) for part in (author.get("given"), author.get("family")) if part)
                    if full_name:
                        authors.append(full_name)
            content = clean_markup(str(abstract)) if abstract else "暂无摘要，请打开原文查看完整内容。"
            documents.append({"title": html.unescape(str(title)), "url": str(url), "content": content, "content_level": "abstract" if abstract else "metadata", "published_at": published, "authors": authors})
    return documents


def _parse_openalex(payload: bytes) -> list[dict[str, object]]:
    data = json.loads(payload.decode("utf-8"))
    documents = []
    for item in data.get("results", []) if isinstance(data, dict) else []:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        url = item.get("doi") or item.get("id")
        published = _parse_datetime(item.get("publication_date"))
        authors = [((author.get("author") or {}).get("display_name") or "") for author in item.get("authorships", []) if isinstance(author, dict)]
        abstract = item.get("abstract_inverted_index") or {}
        abstract_text = " ".join(abstract.keys()) if isinstance(abstract, dict) else ""
        if title and url:
            documents.append({"title": str(title), "url": str(url), "content": abstract_text or "暂无摘要，请打开原文查看完整内容。", "content_level": "abstract" if abstract_text else "metadata", "published_at": published, "authors": [author for author in authors if author]})
    return documents


def _parse_google_patents(payload: bytes) -> list[dict[str, object]]:
    data = json.loads(payload.decode("utf-8"))
    documents = []
    candidates = data.get("results", []) if isinstance(data, dict) else []
    for item in candidates:
        patent = item.get("patent", item) if isinstance(item, dict) else {}
        if not isinstance(patent, dict):
            continue
        number = patent.get("publication_number") or patent.get("publicationNumber") or patent.get("patent_number")
        title = patent.get("title") or patent.get("patent_title")
        if isinstance(title, dict):
            title = title.get("text") or title.get("value")
        published = _parse_datetime(str(patent.get("publication_date") or patent.get("publicationDate") or ""))
        if number and title:
            number = str(number)
            documents.append({"title": html.unescape(str(title)), "url": f"https://patents.google.com/patent/{number}/en", "content": clean_markup(str(patent.get("snippet") or patent.get("abstract") or "Patent record from Google Patents.")), "content_level": "abstract", "published_at": published, "authors": [str(item.get("name")) for item in patent.get("inventor", []) if isinstance(item, dict) and item.get("name")]})
    return documents


def _parse_semantic_scholar(payload: bytes) -> list[dict[str, object]]:
    data = json.loads(payload.decode("utf-8"))
    documents = []
    for item in data.get("data", []) if isinstance(data, dict) else []:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        url = item.get("url") or (f"https://www.semanticscholar.org/paper/{item.get('paperId')}" if item.get("paperId") else None)
        published = _parse_datetime(item.get("publicationDate"))
        if url and published:
            documents.append({"title": str(item["title"]), "url": str(url), "content": clean_markup(str(item.get("abstract") or "暂无摘要，请打开原文查看完整内容。")), "content_level": "abstract" if item.get("abstract") else "metadata", "published_at": published, "authors": [str(author.get("name")) for author in item.get("authors", []) if isinstance(author, dict) and author.get("name")]})
    return documents


def _parse_europe_pmc(payload: bytes) -> list[dict[str, object]]:
    data = json.loads(payload.decode("utf-8"))
    results = ((data.get("resultList") or {}).get("result", [])) if isinstance(data, dict) else []
    documents = []
    for item in results:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        identifier = item.get("doi") or item.get("pmcid") or item.get("id")
        if not identifier:
            continue
        url = f"https://doi.org/{identifier}" if item.get("doi") else f"https://europepmc.org/article/{'PMC' if item.get('pmcid') else 'MED'}/{identifier}"
        published = _parse_datetime(str(item.get("firstPublicationDate") or item.get("electronicPublicationDate") or ""))
        if published:
            documents.append({"title": str(item["title"]), "url": url, "content": clean_markup(str(item.get("abstractText") or "暂无摘要，请打开原文查看完整内容。")), "content_level": "abstract" if item.get("abstractText") else "metadata", "published_at": published, "authors": [str(item.get("authorString"))] if item.get("authorString") else []})
    return documents


def _parse_patentsview(payload: bytes) -> list[dict[str, object]]:
    data = json.loads(payload.decode("utf-8"))
    patents = data.get("patents") or data.get("results") or [] if isinstance(data, dict) else []
    documents = []
    for item in patents:
        if not isinstance(item, dict):
            continue
        number = item.get("patent_id") or item.get("patent_number") or item.get("publication_number")
        title = item.get("patent_title") or item.get("title")
        published = _parse_datetime(str(item.get("patent_date") or item.get("publication_date") or ""))
        if number and title and published:
            documents.append({"title": str(title), "url": f"https://patents.google.com/patent/{number}/en", "content": clean_markup(str(item.get("patent_abstract") or item.get("abstract") or "Patent record from PatentsView.")), "content_level": "abstract", "published_at": published, "authors": []})
    return documents


def parse_payload(payload: bytes, content_type: str, format_name: str | None = None, source_url: str = "") -> list[dict[str, object]]:
    if format_name == "html":
        return _parse_html(payload, source_url)
    if format_name == "openalex":
        return _parse_openalex(payload)
    if format_name == "google_patents":
        return _parse_google_patents(payload)
    if format_name == "semantic_scholar":
        return _parse_semantic_scholar(payload)
    if format_name == "europe_pmc":
        return _parse_europe_pmc(payload)
    if format_name == "patentsview":
        return _parse_patentsview(payload)
    if format_name in {"json", "crossref"} or "json" in content_type:
        return _parse_json(payload)
    return _parse_xml(payload)


def _page_url(source_url: str, format_name: str, page: int, page_size: int) -> str:
    """Build a second page for providers that expose conventional offsets."""
    if page <= 0 or format_name in {"rss", "html", "google_patents", "patentsview"}:
        return source_url
    parsed = urlparse(source_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if format_name == "arxiv":
        query["start"] = str(page * page_size)
        query["max_results"] = str(page_size)
    elif format_name == "openalex":
        query["page"] = str(page + 1)
        query["per-page"] = str(page_size)
    elif format_name == "crossref":
        query["offset"] = str(page * page_size)
        query["rows"] = str(page_size)
    elif format_name == "semantic_scholar":
        query["offset"] = str(page * page_size)
        query["limit"] = str(min(page_size, 100))
    elif format_name == "europe_pmc":
        query["page"] = str(page + 1)
        query["pageSize"] = str(page_size)
    else:
        return source_url
    return urlunparse(parsed._replace(query=urlencode(query)))


AGGREGATOR_HOSTS = {"news.google.com", "finance.biggo.com", "www.biggo.com", "biggo.com"}


def _enrich_aggregated_record(record: dict[str, object], fetcher: Fetcher) -> dict[str, object]:
    """Follow common feed/aggregator links and keep the publisher's article URL/content."""
    original_url = str(record.get("url") or "")
    host = urlparse(original_url).netloc.lower().split(":", 1)[0]
    if host not in AGGREGATOR_HOSTS:
        return record
    try:
        payload, content_type = fetcher(original_url, timeout=settings.source_article_enrich_timeout_seconds) if fetcher is fetch_url else fetcher(original_url)
        if "html" not in content_type:
            return record
        page = parse_payload(payload, content_type, "html", original_url)
        if not page:
            return record
        enriched = dict(record)
        enriched.update({key: page[0][key] for key in ("url", "title", "content", "content_level", "authors") if page[0].get(key)})
        return enriched
    except Exception:
        return record


def ingest_source(db: Session, source: Source, fetcher: Fetcher = fetch_url) -> dict[str, object]:
    if not source.url:
        return {"fetched": 0, "created": 0, "duplicates": 0, "status": "skipped", "error": "source has no URL"}
    format_name = (source.raw_metadata or {}).get("format")
    if not format_name:
        return {"fetched": 0, "created": 0, "duplicates": 0, "status": "skipped", "error": "source has no ingestion format"}
    if format_name == "patentsview" and not settings.patentsview_api_key:
        return {"fetched": 0, "created": 0, "duplicates": 0, "status": "skipped", "error": "PATENTSVIEW_API_KEY is not configured"}
    try:
        headers = {"X-Api-Key": settings.patentsview_api_key} if format_name == "patentsview" and settings.patentsview_api_key else None
        metadata = source.raw_metadata or {}
        try:
            max_pages = max(1, min(5, int(metadata.get("max_pages", 1))))
            page_size = max(1, min(100, int(metadata.get("page_size", 50))))
        except (TypeError, ValueError):
            max_pages, page_size = 1, 50
        records: list[dict[str, object]] = []
        for page in range(max_pages):
            page_url = _page_url(source.url, format_name, page, page_size)
            payload, content_type = fetch_url(page_url, headers) if fetcher is fetch_url else fetcher(page_url)
            page_records = parse_payload(payload, content_type, format_name, page_url)
            records.extend(page_records)
            if not page_records:
                break
        created = 0
        duplicates = 0
        seen_urls: set[str] = set()
        seen_fingerprints: set[str] = set()
        article_enrich_budget = settings.source_article_enrich_limit
        for record in records:
            record_url = str(record.get("url") or "")
            record_host = urlparse(record_url).netloc.lower().split(":", 1)[0]
            if article_enrich_budget > 0 and record_host in AGGREGATOR_HOSTS:
                record = _enrich_aggregated_record(record, fetch_url if fetcher is fetch_url else fetcher)
                article_enrich_budget -= 1
            canonical_url = str(record["url"] or source.url)
            title = str(record["title"])
            content = str(record["content"])
            published_at = record.get("published_at")
            if not published_at or published_at.year != utc_now().year:
                continue
            fingerprint = hashlib.sha256(f"{title}\n{content}".encode("utf-8")).hexdigest()
            existing = db.scalar(select(Document).where((Document.canonical_url == canonical_url) | (Document.content_fingerprint == fingerprint)))
            if existing or canonical_url in seen_urls or fingerprint in seen_fingerprints:
                duplicates += 1
                if existing and existing.canonical_url == canonical_url:
                    existing.title = title
                    existing.content_text = content
                    existing.content_level = record.get("content_level", "metadata")
                    if record.get("authors"):
                        existing.authors = record["authors"]
                continue
            db.add(Document(
                id=f"doc-{hashlib.sha256(canonical_url.encode('utf-8')).hexdigest()[:24]}",
                source_id=source.id,
                canonical_url=canonical_url,
                title=title,
                content_text=content,
                authors=record.get("authors", []),
                content_level=record.get("content_level", "metadata"),
                published_at=published_at,
                fetched_at=utc_now(),
                content_fingerprint=fingerprint,
                raw_metadata={"ingestion": "rss_or_json"},
            ))
            seen_urls.add(canonical_url)
            seen_fingerprints.add(fingerprint)
            created += 1
        db.commit()
        return {"fetched": len(records), "created": created, "duplicates": duplicates, "status": "ok"}
    except Exception as error:
        db.rollback()
        return {"fetched": 0, "created": 0, "duplicates": 0, "status": "error", "error": str(error)}
