from __future__ import annotations

import hashlib
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RadarRun, Source, utc_now
from app.services.analyzer import analyze_pending_documents
from app.services.ai_gateway import active_provider
from app.services.ai_search import search_and_store
from app.services.ingestion import ingest_source


def run_radar(db: Session) -> RadarRun:
    run = RadarRun(id=f"run-{hashlib.sha256(utc_now().isoformat().encode('utf-8')).hexdigest()[:24]}", started_at=utc_now(), status="running", errors=[])
    sources = [source for source in db.scalars(select(Source).order_by(Source.title.asc())).all() if source.enabled and (source.raw_metadata or {}).get("format") not in {None, "ai_search"}]
    run.source_count = len(sources)
    db.add(run)
    db.commit()
    try:
        for source in sources:
            result = ingest_source(db, source)
            source.last_checked_at = utc_now()
            source.last_error = result.get("error")
            run.documents_fetched += int(result.get("fetched", 0))
            run.documents_created += int(result.get("created", 0))
            if result.get("status") == "error":
                run.errors.append(f"{source.title}: {result.get('error', 'unknown error')}")
        if active_provider(web_search=True) != "rule_based" and settings.openai_ai_search_enabled:
            run.source_count += 1
            ai_result = search_and_store(db)
            run.documents_fetched += int(ai_result.get("fetched", 0))
            run.documents_created += int(ai_result.get("created", 0))
            if ai_result.get("status") == "error":
                run.errors.append(f"AI Web Search: {ai_result.get('error', 'unknown error')}")
        analyses, generated_changes = analyze_pending_documents(db)
        run.analyzed = len(analyses)
        run.relevant = sum(1 for analysis in analyses if analysis.is_relevant)
        run.generated_changes = generated_changes
        run.status = "completed_with_errors" if run.errors else "completed"
    except Exception as error:
        db.rollback()
        run = db.get(RadarRun, run.id)
        if run is None:
            raise
        run.status = "failed"
        run.errors = [str(error)]
    run.finished_at = utc_now()
    db.commit()
    db.refresh(run)
    return run
