from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import Change, Document, Source, WatchItem
from app.services.analyzer import analyze_pending_documents
from app.services.ingestion import ingest_source, parse_payload


def test_parse_arxiv_atom_feed() -> None:
    payload = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Glass core substrate study</title><id>https://arxiv.org/abs/1234.5678</id><summary>New TGV reliability results.</summary><published>2026-07-11T00:00:00Z</published></entry></feed>'''

    documents = parse_payload(payload, "application/atom+xml", "arxiv")

    assert documents == [
        {
            "title": "Glass core substrate study",
            "url": "https://arxiv.org/abs/1234.5678",
            "content": "New TGV reliability results.",
            "published_at": documents[0]["published_at"],
            "authors": [],
            "content_level": "abstract",
        }
    ]


def test_parse_public_html_page() -> None:
    payload = b'<html><head><title>Glass substrate news</title><link rel="canonical" href="https://publisher.test/glass"/><meta name="author" content="Intel"></head><body><h1>Glass substrate news</h1><p>Intel announced a glass substrate for advanced packaging.</p></body></html>'

    documents = parse_payload(payload, "text/html", "html", "https://example.test/news")

    assert documents[0]["title"] == "Glass substrate news"
    assert documents[0]["url"] == "https://publisher.test/glass"
    assert documents[0]["authors"] == ["Intel"]
    assert documents[0]["content_level"] == "full_text"
    assert "advanced packaging" in documents[0]["content"]


def test_recent_documents_endpoint_starts_empty() -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    response = TestClient(app).get("/api/documents/recent")

    assert response.status_code == 200
    assert response.json() == []


def test_ingestion_deduplicates_by_url_and_fingerprint() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    payload = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Glass core substrate study</title><id>https://arxiv.org/abs/1234.5678</id><summary>New TGV reliability results.</summary><published>2026-07-11T00:00:00Z</published></entry></feed>'''
    with Session(engine) as db:
        source = Source(id="src-test", source_type="paper_feed", title="Test feed", url="https://example.test/feed", raw_metadata={"format": "arxiv"})
        db.add(source)
        db.commit()
        fetcher = lambda url: (payload, "application/atom+xml")

        first = ingest_source(db, source, fetcher)
        second = ingest_source(db, source, fetcher)

    assert first["created"] == 1
    assert second["created"] == 0
    assert second["duplicates"] == 1


def test_rule_analysis_generates_relevant_change(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "ai_provider", "rule_based")
    monkeypatch.setattr(settings, "dify_api_key", None)
    monkeypatch.setattr(settings, "openai_api_key", None)
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        source = Source(id="src-test-analysis", source_type="paper_feed", title="Test paper feed", url="https://example.test/feed", raw_metadata={"format": "arxiv"})
        item = WatchItem(id="topic-glass-core", kind="topic", name="Glass Core", is_following=True)
        db.add_all([source, item])
        db.flush()
        db.add(Document(id="doc-test-analysis", source_id=source.id, canonical_url="https://example.test/doc", title="Glass Core TGV reliability", content_text="New Glass Core TGV reliability results show a stronger engineering signal.", content_fingerprint="fingerprint-test-analysis", raw_metadata={}))
        db.commit()

        analyses, generated = analyze_pending_documents(db)

        change = db.get(Change, "chg-doc-test-analysis")
        assert len(analyses) == 1
        assert analyses[0].is_relevant is True
        assert analyses[0].category == "university"
        assert generated == 1
        assert change is not None
        assert change.watch_item_ids == ["topic-glass-core"]
