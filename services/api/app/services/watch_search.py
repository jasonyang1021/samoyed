from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Document, Lab, Source, WatchItem, utc_now
from app.services.ai_gateway import AIUnavailableError, active_provider, call_ai_json
from app.services.ingestion import is_recent

WATCH_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {"results": {"type": "array", "items": {"type": "object", "properties": {
        "title": {"type": "string"}, "url": {"type": "string"}, "summary": {"type": "string"},
        "published_at": {"type": ["string", "null"]}, "image_url": {"type": ["string", "null"]}, "source_type": {"type": "string"},
    }, "required": ["title", "url", "summary", "published_at", "image_url", "source_type"], "additionalProperties": False}}},
    "required": ["results"], "additionalProperties": False,
}


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def search_watch_item(db: Session, lab: Lab, item: WatchItem) -> None:
    if active_provider(web_search=True) != "dify":
        raise AIUnavailableError("Dify Web Search is not configured")
    prompt = f"""Search the public web for the latest reliable information about: {item.name}.
Lab: {lab.name}. Research context: {lab.description or 'not provided'}.
Find up to 12 papers, company updates, patents, conference materials, or reputable news items published within the last {settings.source_lookback_days} days.
Prefer official sources, publishers, universities, patent offices, and primary research. Return real public URLs only.
Include a concise factual summary and an image URL only when a real article image is available. Return the requested JSON."""
    result = call_ai_json(prompt, "watch_item_web_search", WATCH_SEARCH_SCHEMA, web_search=True)
    source = db.get(Source, "src-ai-web-search")
    if source is None:
        source = Source(id="src-ai-web-search", source_type="ai_web_search", title="Dify · 关注对象联网检索", url=None, raw_metadata={"provider": "dify", "format": "ai_search"})
        db.add(source)
        db.flush()
    for row in (result.get("results", []) if isinstance(result, dict) else [])[:12]:
        if not isinstance(row, dict) or not row.get("title") or not row.get("url"):
            continue
        url, title = str(row["url"]), str(row["title"])
        summary = str(row.get("summary") or "暂无摘要。")
        published_at = _parse_date(row.get("published_at"))
        if not is_recent(published_at):
            continue
        if db.query(Document).filter(Document.canonical_url == url).first() is not None:
            continue
        db.add(Document(id=f"doc-{hashlib.sha256(url.encode('utf-8')).hexdigest()[:24]}", source_id=source.id, canonical_url=url, title=title, content_text=f"{item.name}\n{summary}", authors=[], content_level="abstract", published_at=published_at, fetched_at=utc_now(), content_fingerprint=hashlib.sha256(f"{title}\n{summary}".encode("utf-8")).hexdigest(), raw_metadata={"ingestion": "dify_watch_search", "watch_item_id": item.id, "image_url": row.get("image_url"), "source_type": row.get("source_type", "web")}))
    db.commit()
