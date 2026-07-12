from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RadarRun, Source, utc_now
from app.services.analyzer import analyze_pending_documents
from app.services.ai_gateway import active_provider
from app.services.ai_search import search_and_store
from app.services.ingestion import ingest_source


def run_radar(db: Session, run: RadarRun | None = None) -> RadarRun:
    run = run or RadarRun(id=f"run-{hashlib.sha256(utc_now().isoformat().encode('utf-8')).hexdigest()[:24]}", started_at=utc_now(), status="running", errors=[])
    errors: list[str] = []
    documents_fetched = 0
    documents_created = 0
    sources = [source for source in db.scalars(select(Source).order_by(Source.title.asc())).all() if source.enabled and (source.raw_metadata or {}).get("format") not in {None, "ai_search"}]
    run.source_count = len(sources)
    run.total_sources = len(sources)
    run.phase = "ingestion"
    if run not in db:
        db.add(run)
    db.commit()
    try:
        for source in sources:
            run.current_source = source.title
            db.commit()
            metadata = dict(source.raw_metadata or {})
            health = dict(metadata.get("health") or {})
            last_failure_at = health.get("last_failure_at")
            if int(health.get("consecutive_failures", 0)) >= 3 and last_failure_at:
                try:
                    if utc_now() < datetime.fromisoformat(last_failure_at) + timedelta(hours=1):
                        errors.append(f"{source.title}: 暂停抓取，等待健康冷却窗口结束")
                        continue
                except (TypeError, ValueError):
                    pass
            result = ingest_source(db, source)
            source.last_checked_at = utc_now()
            source.last_error = result.get("error")
            if result.get("status") == "error":
                health["consecutive_failures"] = int(health.get("consecutive_failures", 0)) + 1
                health["last_failure_at"] = utc_now().isoformat()
                health["last_error"] = str(result.get("error") or "unknown error")
            else:
                health["consecutive_failures"] = 0
                health["last_success_at"] = utc_now().isoformat()
                health.pop("last_error", None)
            metadata["health"] = health
            source.raw_metadata = metadata
            documents_fetched += int(result.get("fetched", 0))
            documents_created += int(result.get("created", 0))
            if result.get("status") == "error":
                errors.append(f"{source.title}: {result.get('error', 'unknown error')}")
            run.documents_fetched = documents_fetched
            run.documents_created = documents_created
            run.processed_sources += 1
            run.errors = errors
            db.commit()
        if active_provider(web_search=True) != "rule_based" and settings.openai_ai_search_enabled:
            run.phase = "ai_search"
            run.current_source = "AI Web Search"
            db.commit()
            run.source_count += 1
            try:
                ai_result = search_and_store(db)
                documents_fetched += int(ai_result.get("fetched", 0))
                documents_created += int(ai_result.get("created", 0))
                if ai_result.get("status") == "error":
                    errors.append(f"AI Web Search: {ai_result.get('error', 'unknown error')}")
            except Exception as error:
                # AI web search is an optional enrichment step. A provider
                # timeout must not discard the normal source ingestion run.
                errors.append(f"AI Web Search：{error}")
            run.documents_fetched = documents_fetched
            run.documents_created = documents_created
            run.errors = errors
            db.commit()
        try:
            run.phase = "analysis"
            run.current_source = "AI Analysis"
            run.analysis_total = 0
            run.dify_requests_total = 0
            run.dify_requests_succeeded = 0
            run.dify_requests_failed = 0
            run.analyzed = 0
            db.commit()

            def report_analysis_progress(event: str, value: int) -> None:
                if event == "analysis_started":
                    run.analysis_total = value
                    run.current_source = f"AI Analysis · 准备分析 {value} 条资料"
                elif event == "dify_started":
                    run.dify_requests_total += 1
                    run.current_source = f"AI Analysis · Dify 请求 {run.dify_requests_total}（处理中）"
                elif event == "dify_succeeded":
                    run.dify_requests_succeeded += 1
                    run.current_source = f"AI Analysis · Dify 已成功 {run.dify_requests_succeeded}/{run.dify_requests_total}"
                elif event == "dify_failed":
                    run.dify_requests_failed += 1
                    run.current_source = f"AI Analysis · Dify 已完成 {run.dify_requests_succeeded}，失败 {run.dify_requests_failed}"
                elif event == "document_completed":
                    run.analyzed = value
                    run.current_source = f"AI Analysis · 已分析 {value}/{run.analysis_total}，Dify 成功 {run.dify_requests_succeeded}/{run.dify_requests_total}"
                db.commit()

            analyses, generated_changes = analyze_pending_documents(db, progress_callback=report_analysis_progress)
            run.analyzed = len(analyses)
            run.relevant = sum(1 for analysis in analyses if analysis.is_relevant)
            run.generated_changes = generated_changes
        except Exception as error:
            # Keep ingestion results usable when a large analysis batch or an
            # external provider times out. Remaining documents can be analyzed
            # by the next run instead of turning the whole radar run into a loss.
            errors.append(f"分析阶段：{error}")
            run.analyzed = 0
            run.relevant = 0
            run.generated_changes = 0
        run.documents_fetched = documents_fetched
        run.documents_created = documents_created
        run.errors = errors
        run.status = "completed_with_errors" if errors else "completed"
        run.phase = "completed"
        run.current_source = None
    except Exception as error:
        db.rollback()
        run = db.get(RadarRun, run.id)
        if run is None:
            raise
        run.status = "failed"
        run.phase = "failed"
        run.current_source = None
        run.documents_fetched = documents_fetched
        run.documents_created = documents_created
        run.errors = [*errors, str(error)]
    run.finished_at = utc_now()
    db.commit()
    db.refresh(run)
    return run
