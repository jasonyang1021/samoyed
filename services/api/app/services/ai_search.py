from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, LabWatchItem, Source, WatchItem, utc_now
from app.services.ai_gateway import AIUnavailableError, active_provider, call_ai_json
from app.services.ingestion import clean_markup, is_recent


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


def _search_terms(items: list[WatchItem]) -> str:
    related_terms = []
    for item in items:
        name = item.name.casefold()
        if "hbm" in name or "memory" in name:
            related_terms.extend(["HBM3E", "HBM4", "high bandwidth memory", "memory packaging", "TSV", "2.5D packaging"])
        if "glass" in name or "tgv" in name:
            related_terms.extend(["glass substrate", "glass core", "through glass via", "TGV", "glass interposer"])
        if "packag" in name or "chiplet" in name:
            related_terms.extend(["advanced packaging", "chiplet", "2.5D", "3D integration", "interposer"])
    return ", ".join(dict.fromkeys([*related_terms, *[item.name for item in items]]))


def _watch_query(items: list[WatchItem]) -> str:
    names = ", ".join(item.name for item in items)
    terms = _search_terms(items)
    return (
        f"Search public information published within the last {settings.source_lookback_days} days only. "
        f"Search these topics and related terms: {terms}. "
        f"Prioritize the Lab-configured watch items: {names}. "
        "Return up to 30 high-quality results across four lanes: research papers and preprints, patents, conference proceedings, and official company or laboratory updates. "
        "For papers prefer arXiv, OpenAlex, Crossref, Semantic Scholar, publishers, and universities. "
        "For patents prefer USPTO, PatentsView, WIPO, EPO, J-PlatPat, CNIPA, or an exact Google Patents record. "
        "Every result must include a real public URL, an exact publication date within the time window, a concise factual summary, and a precise source_type such as paper, patent, conference, or company."
    )


def _parse_date(value: Any):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def search_and_store(db: Session) -> dict[str, object]:
    if active_provider(web_search=True) == "rule_based" or not settings.openai_ai_search_enabled:
        return {"fetched": 0, "created": 0, "status": "skipped", "error": "AI search is not configured"}
    items = db.scalars(select(WatchItem).where(WatchItem.is_following.is_(True)).order_by(WatchItem.name.asc())).all()
    if not items:
        return {"fetched": 0, "created": 0, "status": "skipped", "error": "no followed items"}
    terms = _search_terms(items)
    try:
        result = call_ai_json(_watch_query(items), "research_radar_search", SEARCH_SCHEMA, web_search=True)
        if not result.get("results"):
            result = call_ai_json(
                f"Search the web now for recent papers, patents, conference proceedings, and company updates from the last {settings.source_lookback_days} days about {terms}. "
                "You must return at least 3 results when public sources exist. Include the exact title, real URL, source_type, publication date and a short factual summary for each result. "
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
        if not is_recent(published_at):
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
