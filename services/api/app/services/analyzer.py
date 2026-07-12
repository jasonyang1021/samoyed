from __future__ import annotations

import hashlib
import re
from datetime import timedelta
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Analysis, Change, Document, Lab, LabChangeInterpretation, LabSource, LabWatchItem, WatchItem, utc_now
from app.services.ai_gateway import AIUnavailableError, active_provider, call_ai_json


KEYWORDS = (
    "glass core",
    "glass-core",
    "tgv",
    "through glass via",
    "advanced packaging",
    "hbm",
    "high bandwidth memory",
    "cpo",
    "co-packaged optics",
    "optical interconnect",
    "pcb",
    "printed circuit board",
    "mlcc",
    "multilayer ceramic capacitor",
)
DOMAIN_TERMS = (
    "substrate",
    "tgv",
    "through glass via",
    "advanced packaging",
    "interconnect",
    "reliability",
    "warpage",
    "semiconductor",
    "hbm",
    "high bandwidth memory",
    "cpo",
    "co-packaged optics",
    "optical",
    "photonics",
    "pcb",
    "printed circuit",
    "laminate",
    "signal integrity",
    "mlcc",
    "ceramic capacitor",
    "package",
    "packaging",
)

AI_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "relevance_score": {"type": "number"},
        "is_relevant": {"type": "boolean"},
        "category": {"type": "string", "enum": ["patent", "company", "university", "conference", "technology"]},
        "matched_entities": {"type": "array", "items": {"type": "string"}},
        "extracted_facts": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
        "previous_state": {"type": "string"},
        "current_state": {"type": "string"},
        "change_summary": {"type": "string"},
        "importance": {"type": "string", "enum": ["S", "A", "B", "C"]},
        "lab_why_relevant": {"type": "string"},
        "lab_impact": {"type": "string"},
        "confidence": {"type": "number"},
        "evidence_citations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["relevance_score", "is_relevant", "category", "matched_entities", "extracted_facts", "summary", "previous_state", "current_state", "change_summary", "importance", "lab_why_relevant", "lab_impact"],
    "additionalProperties": False,
}


def _ai_analyze(document: Document, watched_names: list[str], profiles: list[dict], progress_callback: Callable[[str, int], None] | None = None) -> dict[str, object] | None:
    if active_provider() == "rule_based":
        return None
    prompt = f"""You are the senior analyst for AI Research Radar.
Analyze this public research item against the Lab profiles below. Do not invent facts. Treat the supplied text as the source of truth. Use only the configured Lab scopes and signal rules; do not assume a particular industry.
Followed entities: {', '.join(watched_names) or 'none'}
Lab profiles: {profiles}
Title: {document.title}
Authors: {', '.join(document.authors or []) or 'not provided'}
Source: {document.source.title}
URL: {document.canonical_url}
Content:
{document.content_text[:settings.ai_max_input_chars]}

Decide whether it is materially relevant to any configured Lab. Return concise Chinese text for the summary and all judgment fields. Keep extracted_facts and evidence_citations to at most three items. Each evidence_citations item must be a short verbatim quote or a precise location in the supplied source. Confidence and relevance_score must be between 0 and 1."""
    try:
        if progress_callback:
            progress_callback("dify_started", 0)
        result = call_ai_json(prompt, "research_radar_analysis", AI_ANALYSIS_SCHEMA)
        if progress_callback:
            progress_callback("dify_succeeded", 0)
        result["relevance_score"] = max(0.0, min(0.99, float(result["relevance_score"])))
        result["confidence"] = max(0.0, min(0.99, float(result.get("confidence", result["relevance_score"]))))
        result["evidence_citations"] = [str(item) for item in result.get("evidence_citations", [])][:3]
        return result
    except (AIUnavailableError, KeyError, TypeError, ValueError):
        if progress_callback:
            progress_callback("dify_failed", 0)
        return None


def _summary(text: str, fallback_title: str = "") -> str:
    if text.startswith("暂无摘要"):
        return f"{fallback_title}（来源未提供摘要）"[:240]
    sentence = re.split(r"(?<=[.!?。！？])\s+", text.strip())[0]
    return sentence[:240] or "发现一条新的研究资料。"


def _category(source_type: str, matched_entities: list[str], title: str) -> str:
    lower_title = title.lower()
    if "patent" in source_type.lower() or "专利" in lower_title:
        return "patent"
    if any(name in matched_entities for name in ("Intel", "Samsung", "Absolics", "TSMC", "Micron", "NVIDIA", "Corning")):
        return "company"
    if "paper" in source_type.lower() or "arxiv" in source_type.lower():
        return "university"
    if "conference" in source_type.lower() or any(name in matched_entities for name in ("ECTC", "IEDM")):
        return "conference"
    return "technology"


def _ensure_lab_interpretations(db: Session, change: Change, document: Document, matched_entities: list[str], score: float, ai_result: dict[str, object] | None) -> None:
    haystack = f"{document.title}\n{document.content_text}".casefold()
    linked_names = set(matched_entities)
    for lab in db.scalars(select(Lab).order_by(Lab.name.asc())).all():
        selected_sources = {link.source_id for link in db.query(LabSource).filter(LabSource.lab_id == lab.id, LabSource.enabled.is_(True)).all()}
        if selected_sources and document.source_id not in selected_sources:
            continue
        lab_items = {link.watch_item.name for link in db.query(LabWatchItem).filter(LabWatchItem.lab_id == lab.id).all()}
        profile = lab.profile
        configured_rules = profile.signal_rules if profile and isinstance(profile.signal_rules, dict) else {}
        signals = tuple(str(item).casefold() for item in configured_rules.get("keywords", []) if str(item).strip())
        matched_signals = [signal for signal in signals if signal in haystack]
        matched_watch_items = [name for name in lab_items if name.casefold() in haystack or name in linked_names]
        if not matched_signals and not matched_watch_items:
            continue
        relevance = min(0.99, max(0.45, score + len(matched_signals) * 0.04))
        scope = profile.research_scope if profile and isinstance(profile.research_scope, dict) else {}
        scope_terms = [str(item) for value in scope.values() if isinstance(value, list) for item in value]
        scope_label = "、".join(scope_terms[:3]) or "该 Lab 的研究范围"
        why = f"内容命中了 {', '.join(matched_signals[:3]) or '关注项'}，与 {scope_label} 的配置化研究范围相关。"
        impact = "需要结合来源证据和 Lab 的关键问题，判断该信号是否足以改变当前研究判断。"
        if ai_result:
            why = str(ai_result.get("lab_why_relevant") or why)
            impact = str(ai_result.get("lab_impact") or impact)
        interpretation_id = f"interp-{lab.id}-{change.id}"
        interpretation = db.query(LabChangeInterpretation).filter(LabChangeInterpretation.lab_id == lab.id, LabChangeInterpretation.change_id == change.id).first()
        if interpretation is None:
            db.add(LabChangeInterpretation(id=interpretation_id, lab_id=lab.id, change_id=change.id, relevance_score=relevance, why_relevant=why, impact=impact, next_watch_points=["确认是否形成连续证据", "比较不同来源的实验或工程条件"], generation_method="ai" if ai_result else "rule_based"))
        elif ai_result and interpretation.generation_method != "ai":
            interpretation.relevance_score = relevance
            interpretation.why_relevant = why
            interpretation.impact = impact
            interpretation.generation_method = "ai"


def _analyze_document(db: Session, document: Document, progress_callback: Callable[[str, int], None] | None = None) -> tuple[Analysis, Change | None]:
    existing = db.scalar(select(Analysis).where(Analysis.document_id == document.id))
    if existing:
        generated_id = (existing.raw_result or {}).get("generated_change_id")
        return existing, db.get(Change, generated_id) if generated_id else None

    followed_items = db.scalars(select(WatchItem).where(WatchItem.is_following.is_(True))).all()
    followed_names = [item.name for item in followed_items]
    profiles = [{"lab": lab.name, "scope": lab.profile.research_scope if lab.profile else {}, "rules": lab.profile.signal_rules if lab.profile else {}} for lab in db.scalars(select(Lab).order_by(Lab.name.asc())).all()]
    haystack = f"{document.title}\n{document.content_text}".casefold()
    matched_entities = [item.name for item in followed_items if item.name.casefold() in haystack]
    matched_keywords = [keyword for keyword in KEYWORDS if keyword in haystack]
    domain_matches = [term for term in DOMAIN_TERMS if term in haystack]
    score = min(0.99, 0.25 + len(matched_entities) * 0.2 + len(matched_keywords) * 0.18 + len(domain_matches) * 0.08) if domain_matches else 0.15
    is_relevant = bool(domain_matches) and score >= 0.5
    summary = _summary(document.content_text, document.title)
    category = _category(document.source.source_type, matched_entities, document.title)
    # Only send plausible radar candidates to the model. Broad scholarly feeds
    # often contain acronym collisions that should be rejected cheaply first.
    ai_result = _ai_analyze(document, followed_names, profiles, progress_callback) if (is_relevant or matched_keywords) else None
    if ai_result:
        matched_entities = [str(item) for item in ai_result["matched_entities"]]
        score = float(ai_result["relevance_score"])
        is_relevant = bool(ai_result["is_relevant"])
        category = str(ai_result["category"])
        summary = str(ai_result["summary"])
        extracted_facts = [str(item) for item in ai_result["extracted_facts"]]
        confidence = float(ai_result.get("confidence", score))
        evidence_citations = [str(item) for item in ai_result.get("evidence_citations", [])]
    else:
        extracted_facts = [summary] if is_relevant else []
        confidence = round(min(0.8, score), 2)
        evidence_citations = [summary] if is_relevant else []
    provider = active_provider() if ai_result else "rule_based"
    analysis = Analysis(
        id=f"analysis-{hashlib.sha256(document.id.encode('utf-8')).hexdigest()[:24]}",
        document_id=document.id,
        relevance_score=round(score, 2),
        is_relevant=is_relevant,
        category=category,
        matched_entities=matched_entities,
        extracted_facts=extracted_facts,
        summary=summary,
        confidence=round(confidence, 2),
        evidence_citations=evidence_citations,
        provider=provider,
        status="completed",
        raw_result={"matched_keywords": matched_keywords, "ai_provider": provider},
    )
    db.add(analysis)
    change = None
    if is_relevant:
        importance = "S" if score >= 0.85 else "A" if score >= 0.7 else "B"
        change_id = f"chg-{document.id}"
        change = db.get(Change, change_id)
        if change is None:
            matched_ids = [item.id for item in db.scalars(select(WatchItem).where(WatchItem.name.in_(matched_entities))).all()]
            change = Change(
                id=change_id,
                title=document.title,
                new_facts=extracted_facts or [summary],
                previous_state=str(ai_result.get("previous_state", "此前公开资料中尚未出现这条新信号。")) if ai_result else "此前公开资料中尚未出现这条新信号。",
                current_state=str(ai_result.get("current_state", summary)) if ai_result else summary,
                change_summary=str(ai_result.get("change_summary", summary)) if ai_result else summary,
                importance=str(ai_result.get("importance", importance)) if ai_result else importance,
                evidence=[{"source_id": document.source_id, "source_title": document.source.title, "evidence_text": summary, "citations": evidence_citations, "url": document.canonical_url, "document_id": document.id, "ai_provider": provider, "confidence": confidence}],
                next_watch_points=["确认是否出现更多独立来源", "观察后续工程验证或引用情况"],
                watch_item_ids=matched_ids,
                status="detected",
                detected_at=utc_now(),
            )
            db.add(change)
            _ensure_lab_interpretations(db, change, document, matched_entities, score, ai_result)
        analysis.raw_result = {**(analysis.raw_result or {}), "generated_change_id": change.id}
    return analysis, change


def analyze_pending_documents(db: Session, document_id: str | None = None, progress_callback: Callable[[str, int], None] | None = None) -> tuple[list[Analysis], int]:
    query = select(Document).order_by(Document.fetched_at.asc())
    if document_id:
        query = query.where(Document.id == document_id)
    else:
        cutoff = utc_now() - timedelta(days=settings.source_lookback_days)
        query = query.where(~Document.id.in_(select(Analysis.document_id)), Document.published_at.is_not(None), Document.published_at >= cutoff).limit(settings.radar_max_documents_per_run)
    documents = db.scalars(query).all()
    if progress_callback:
        progress_callback("analysis_started", len(documents))
    analyses = []
    generated_changes = 0
    for index, document in enumerate(documents, start=1):
        analysis, change = _analyze_document(db, document, progress_callback)
        analyses.append(analysis)
        if change:
            generated_changes += 1
        if progress_callback:
            progress_callback("document_completed", index)
    db.commit()
    return analyses, generated_changes
