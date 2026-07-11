from __future__ import annotations

import hashlib
import re
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Analysis, Change, Document, Lab, LabChangeInterpretation, LabWatchItem, WatchItem, utc_now
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
    },
    "required": ["relevance_score", "is_relevant", "category", "matched_entities", "extracted_facts", "summary", "previous_state", "current_state", "change_summary", "importance", "lab_why_relevant", "lab_impact"],
    "additionalProperties": False,
}


def _ai_analyze(document: Document, watched_names: list[str]) -> dict[str, object] | None:
    if active_provider() == "rule_based":
        return None
    prompt = f"""You are the senior analyst for AI Research Radar.
Analyze this public research item for AI hardware research labs covering Glass Core, PCB, CPO, MLCC, HBM, advanced packaging, interconnect, reliability, and thermal/system integration. Do not invent facts. Treat the supplied text as the source of truth.
Followed entities: {', '.join(watched_names) or 'none'}
Title: {document.title}
Authors: {', '.join(document.authors or []) or 'not provided'}
Source: {document.source.title}
URL: {document.canonical_url}
Content:
{document.content_text[:12000]}

Decide whether it is materially relevant to any followed AI hardware lab topic, including glass substrates, PCB materials, CPO/optical interconnect, MLCC/passives, HBM/memory packaging, advanced packaging, reliability, interconnects, cooling, or adjacent semiconductor packaging. Return concise Chinese text for the summary and all judgment fields. Keep extracted_facts to at most three items. Relevance score must be between 0 and 1."""
    try:
        result = call_ai_json(prompt, "research_radar_analysis", AI_ANALYSIS_SCHEMA)
        result["relevance_score"] = max(0.0, min(0.99, float(result["relevance_score"])))
        return result
    except (AIUnavailableError, KeyError, TypeError, ValueError):
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


LAB_SIGNAL_RULES = {
    "lab-glass-core": ("glass", "tgv", "through glass via", "glass core", "substrate", "warpage"),
    "lab-cpo": ("cpo", "co-packaged optics", "optical interconnect", "photonic", "emib-t"),
    "lab-pcb": ("pcb", "printed circuit", "laminate", "signal integrity", "package substrate", "warpage"),
    "lab-cc": ("cooling", "thermal", "compute", "hbm", "high bandwidth memory", "mlcc", "interconnect", "high bandwidth"),
    "lab-fujii": ("reliability", "materials", "advanced packaging", "tgv", "semiconductor packaging"),
}


def _ensure_lab_interpretations(db: Session, change: Change, document: Document, matched_entities: list[str], score: float, ai_result: dict[str, object] | None) -> None:
    haystack = f"{document.title}\n{document.content_text}".casefold()
    linked_names = set(matched_entities)
    for lab in db.scalars(select(Lab).order_by(Lab.name.asc())).all():
        lab_items = {link.watch_item.name for link in db.query(LabWatchItem).filter(LabWatchItem.lab_id == lab.id).all()}
        signals = LAB_SIGNAL_RULES.get(lab.id, ())
        matched_signals = [signal for signal in signals if signal in haystack]
        matched_watch_items = [name for name in lab_items if name.casefold() in haystack or name in linked_names]
        if not matched_signals and not matched_watch_items:
            continue
        relevance = min(0.99, max(0.45, score + len(matched_signals) * 0.04))
        if lab.id == "lab-glass-core":
            why = "命中了玻璃基板、TGV 或先进封装可靠性信号，与本 Lab 的核心研究范围直接相关。"
            impact = "需要判断该信号是否代表玻璃基板从材料与样品验证继续走向工程化和量产。"
        elif lab.id == "lab-cpo":
            why = "内容涉及光电互连、CPO 或高速封装协同，关联本 Lab 对带宽和光电集成路径的关注。"
            impact = "提示 CPO 的系统瓶颈正在从光学器件延伸到封装、接口和可制造性，需要关注量产验证。"
        elif lab.id == "lab-pcb":
            why = "内容涉及基板材料、翘曲、叠层或信号完整性，与 PCB Lab 的材料和高速设计关注相关。"
            impact = "可能改变 PCB 材料选择、叠层设计或高频互连的工程约束，需比较其对现有工艺的替代程度。"
        elif lab.id == "lab-cc":
            why = "内容触及计算、带宽、互连或热管理，与 CC Lab 的系统级算力和连接效率判断相关。"
            impact = "需要评估该技术是否能转化为系统级带宽、功耗或散热收益，而不只是器件指标提升。"
        else:
            why = "内容涉及材料、可靠性或先进封装验证，与 Fujii Lab 的学术研究和工艺转化关注相关。"
            impact = "可作为后续实验设计和材料路线比较的参考，重点观察是否出现可复现实验和跨机构验证。"
        interpretation_id = f"interp-{lab.id}-{change.id}"
        interpretation = db.query(LabChangeInterpretation).filter(LabChangeInterpretation.lab_id == lab.id, LabChangeInterpretation.change_id == change.id).first()
        if interpretation is None:
            db.add(LabChangeInterpretation(id=interpretation_id, lab_id=lab.id, change_id=change.id, relevance_score=relevance, why_relevant=why, impact=impact, next_watch_points=["确认是否形成连续证据", "比较不同来源的实验或工程条件"], generation_method="ai" if ai_result else "rule_based"))


def _analyze_document(db: Session, document: Document) -> tuple[Analysis, Change | None]:
    existing = db.scalar(select(Analysis).where(Analysis.document_id == document.id))
    if existing:
        generated_id = (existing.raw_result or {}).get("generated_change_id")
        return existing, db.get(Change, generated_id) if generated_id else None

    followed_items = db.scalars(select(WatchItem).where(WatchItem.is_following.is_(True))).all()
    followed_names = [item.name for item in followed_items]
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
    ai_result = _ai_analyze(document, followed_names) if (is_relevant or matched_keywords) else None
    if ai_result:
        matched_entities = [str(item) for item in ai_result["matched_entities"]]
        score = float(ai_result["relevance_score"])
        is_relevant = bool(ai_result["is_relevant"])
        category = str(ai_result["category"])
        summary = str(ai_result["summary"])
        extracted_facts = [str(item) for item in ai_result["extracted_facts"]]
    else:
        extracted_facts = [summary] if is_relevant else []
    analysis = Analysis(
        id=f"analysis-{hashlib.sha256(document.id.encode('utf-8')).hexdigest()[:24]}",
        document_id=document.id,
        relevance_score=round(score, 2),
        is_relevant=is_relevant,
        category=category,
        matched_entities=matched_entities,
        extracted_facts=extracted_facts,
        summary=summary,
        status="completed",
        raw_result={"matched_keywords": matched_keywords, "ai_provider": active_provider() if ai_result else "rule_based"},
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
                evidence=[{"source_id": document.source_id, "source_title": document.source.title, "evidence_text": summary, "url": document.canonical_url, "document_id": document.id, "ai_provider": active_provider() if ai_result else "rule_based"}],
                next_watch_points=["确认是否出现更多独立来源", "观察后续工程验证或引用情况"],
                watch_item_ids=matched_ids,
                status="detected",
                detected_at=utc_now(),
            )
            db.add(change)
            _ensure_lab_interpretations(db, change, document, matched_entities, score, ai_result)
        analysis.raw_result = {**(analysis.raw_result or {}), "generated_change_id": change.id}
    return analysis, change


def analyze_pending_documents(db: Session, document_id: str | None = None) -> tuple[list[Analysis], int]:
    query = select(Document).order_by(Document.fetched_at.asc())
    if document_id:
        query = query.where(Document.id == document_id)
    else:
        query = query.where(~Document.id.in_(select(Analysis.document_id)))
    documents = db.scalars(query).all()
    analyses = []
    generated_changes = 0
    for document in documents:
        analysis, change = _analyze_document(db, document)
        analyses.append(analysis)
        if change:
            generated_changes += 1
    db.commit()
    return analyses, generated_changes
