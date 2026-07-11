from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Callable
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, Source, utc_now

Fetcher = Callable[[str], tuple[bytes, str]]


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title: list[str] = []
        self.text: list[str] = []
        self.authors: list[str] = []
        self.published: str | None = None
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
    return [{"title": title, "url": source_url, "content": content or "暂无网页正文，请打开原文查看完整内容。", "content_level": "full_text" if content else "metadata", "published_at": _parse_datetime(parser.published), "authors": authors}]


def fetch_url(url: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "AI-Research-Radar/0.1"})
    with urlopen(request, timeout=15) as response:
        return response.read(), response.headers.get_content_type()


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


def parse_payload(payload: bytes, content_type: str, format_name: str | None = None, source_url: str = "") -> list[dict[str, object]]:
    if format_name == "html":
        return _parse_html(payload, source_url)
    if format_name == "openalex":
        return _parse_openalex(payload)
    if format_name == "google_patents":
        return _parse_google_patents(payload)
    if format_name in {"json", "crossref"} or "json" in content_type:
        return _parse_json(payload)
    return _parse_xml(payload)


def ingest_source(db: Session, source: Source, fetcher: Fetcher = fetch_url) -> dict[str, object]:
    if not source.url:
        return {"fetched": 0, "created": 0, "duplicates": 0, "status": "skipped", "error": "source has no URL"}
    format_name = (source.raw_metadata or {}).get("format")
    if not format_name:
        return {"fetched": 0, "created": 0, "duplicates": 0, "status": "skipped", "error": "source has no ingestion format"}
    try:
        payload, content_type = fetcher(source.url)
        records = parse_payload(payload, content_type, format_name, source.url)
        created = 0
        duplicates = 0
        seen_urls: set[str] = set()
        seen_fingerprints: set[str] = set()
        for record in records:
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
