from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, LabWatchItem, Source, WatchItem, utc_now
from app.services.ai_gateway import AIUnavailableError, active_provider, call_ai_json
from app.services.ingestion import clean_markup


SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "url": {"type": "string"},
                    "summary": {"type": "string"},
                    "published_at": {"type": ["string", "null"]},
                    "source_type": {"type": "string"},
                    "authors": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title", "url", "summary", "published_at", "source_type", "authors"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}


def _watch_query(items: list[WatchItem]) -> str:
    names = ", ".join(item.name for item in items)
    return (
        "Search recent public information about glass substrates, glass core, TGV and advanced packaging. "
        "Find company news, research papers, patents and conference information from official or reputable sources. "
        f"Also prioritize these Lab-configured watch items: {names}. "
        "Return high-quality results with real public URLs only."
    )


def _parse_date(value: Any):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def search_and_store(db: Session) -> dict[str, object]:
    if active_provider(web_search=True) == "rule_based" or not settings.openai_ai_search_enabled:
        return {"fetched": 0, "created": 0, "status": "skipped", "error": "AI search is not configured"}
    items = db.scalars(select(WatchItem).where(WatchItem.is_following.is_(True)).order_by(WatchItem.name.asc())).all()
    if not items:
        return {"fetched": 0, "created": 0, "status": "skipped", "error": "no followed items"}
    try:
        result = call_ai_json(_watch_query(items), "research_radar_search", SEARCH_SCHEMA, web_search=True)
        if not result.get("results"):
            result = call_ai_json(
                "Search the web now for glass substrate, glass core, TGV and advanced packaging. "
                "You must return at least 3 results when public sources exist. Include the exact title, real URL and a short summary for each result. "
                "Return only the required JSON object.",
                "research_radar_search",
                SEARCH_SCHEMA,
                web_search=True,
            )
    except AIUnavailableError as error:
        return {"fetched": 0, "created": 0, "status": "error", "error": str(error)}

    source = db.scalar(select(Source).where(Source.id == "src-ai-web-search"))
    if source is None:
        source = Source(id="src-ai-web-search", source_type="ai_web_search", title="AI Web Search", url=None, raw_metadata={"provider": "openai", "format": "ai_search"})
        db.add(source)
        db.flush()
    created = 0
    results = result.get("results", []) if isinstance(result, dict) else []
    for item in results:
        if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
            continue
        url = str(item["url"])
        published_at = _parse_date(item.get("published_at"))
        if not published_at or published_at.year != utc_now().year:
            continue
        if db.scalar(select(Document).where(Document.canonical_url == url)):
            continue
        content = clean_markup(str(item.get("summary") or "AI 检索未提供摘要。"))
        db.add(Document(
            id=f"doc-{hashlib.sha256(url.encode('utf-8')).hexdigest()[:24]}",
            source_id=source.id,
            canonical_url=url,
            title=str(item["title"]),
            content_text=content,
            authors=[str(author) for author in item.get("authors", []) if author],
            content_level="abstract",
            published_at=published_at,
            fetched_at=utc_now(),
            content_fingerprint=hashlib.sha256(f"{item['title']}\n{content}".encode("utf-8")).hexdigest(),
            raw_metadata={"ingestion": f"{active_provider(web_search=True)}_web_search", "source_type": item.get("source_type", "web")},
        ))
        created += 1
    db.commit()
    return {"fetched": len(results), "created": created, "status": "ok"}
