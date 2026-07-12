from __future__ import annotations

import json
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

import redis
import secrets
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, create_engine, or_, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.database import SessionLocal, get_db
from app.db.models import Analysis, Change, Document, Lab, LabAuditLog, LabChangeInterpretation, LabInvitation, LabMembership, LabProfile, LabSource, LabWatchItem, RadarRun, RadarSettings, Source, User, WatchItem, utc_now
from app.schemas.analysis import AnalysisRead, AnalysisRunResult
from app.schemas.document import DocumentRead, IngestResult, LabSourceBatchUpdate, LabSourceRead, LabSourceUpdate, SourceRead, SourceRecommendationRead, WatchArticleRead
from app.schemas.change import ChangeCard, ChangeDetail, LabChangeCard
from app.schemas.lab import LabCreate, LabRead, LabUpdate, LabProfileRead, LabProfileUpdate, LabWatchItemCreate, LabWatchItemRead
from app.schemas.radar import RadarRunRead
from app.schemas.watch import WatchItemCreate, WatchItemRead
from app.schemas.schedule import ScheduleRead, ScheduleUpdate
from app.schemas.auth import AuthUserRead, LabInvitationCreate, LabInvitationRead, LabMembershipRead, LabMembershipUpdate
from app.schemas.audit import LabAuditLogRead
from app.services.ingestion import fetch_url, ingest_source
from app.services.analyzer import analyze_pending_documents
from app.services.radar import run_radar
from app.services.ai_gateway import AIUnavailableError, active_model, active_provider, call_ai_json, call_chat_agent, check_dify_connection, parse_json_object, salvage_json_object
from app.services.web_search import search_public_web
from app.services.watch_search import search_watch_item
from app.services.auth import create_session, exchange_google_code, google_authorization_url, google_enabled, google_state, read_session, session_profile, sync_user

router = APIRouter()
logger = logging.getLogger(__name__)


class AssistantAsk(BaseModel):
    question: str = Field(default="", max_length=2000)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)
    context: str = Field(default="", max_length=15000)
    locale: str = Field(default="zh-CN", max_length=10)


ASSISTANT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "learning_summary": {"type": "string"},
        "conclusions": {"type": "array", "items": {"type": "string"}},
        "studied_articles": {"type": "array", "items": {"type": "string"}},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
        "suggested_questions": {"type": "array", "items": {"type": "string"}},
        "source_indexes": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["answer", "learning_summary", "conclusions", "studied_articles", "uncertainties", "suggested_questions", "source_indexes"],
    "additionalProperties": False,
}


def _normalize_assistant_result(result: dict[str, Any]) -> dict[str, Any]:
    result["answer"] = str(result.get("answer") or "我已经完成了这次检索，但暂时没有形成可确认的结论。")
    result["learning_summary"] = str(result.get("learning_summary") or "已读取当前 Lab 的研究上下文。")
    for key in ("conclusions", "studied_articles", "uncertainties", "suggested_questions"):
        value = result.get(key)
        result[key] = [str(item) for item in value] if isinstance(value, list) else []
    indexes = result.get("source_indexes")
    result["source_indexes"] = [int(index) for index in indexes if isinstance(index, (int, float, str)) and str(index).isdigit()] if isinstance(indexes, list) else []
    return result


def _audit_lab_action(db: Session, lab_id: str, actor: Optional[dict], action: str, target: Optional[str], details: dict) -> None:
    actor_user = db.query(User).filter(User.email == (actor or {}).get("email", "").lower()).first()
    db.add(LabAuditLog(id=f"audit-{secrets.token_urlsafe(12)}", lab_id=lab_id, actor_user_id=actor_user.id if actor_user else None, action=action, target=target, details=details, created_at=utc_now()))


def _cross_site_cookie() -> bool:
    frontend = settings.frontend_url.rstrip("/")
    callback_origin = settings.google_redirect_uri.split("/api/auth/google/callback", 1)[0].rstrip("/")
    return frontend.startswith("https://") and callback_origin.startswith("https://") and frontend != callback_origin


def _current_user(request: Request) -> dict | None:
    return read_session(request.cookies.get("radar_session"))


def require_admin(request: Request) -> Optional[dict]:
    if not google_enabled():
        return None
    user = _current_user(request)
    if not user or user.get("role") != "system_admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user


def require_lab_admin(request: Request, lab_id: str, db: Session) -> dict:
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    if not google_enabled() or user.get("role") == "system_admin":
        return user
    stored_user = db.query(User).filter(User.email == (user.get("email") or "").lower()).first()
    membership = db.get(LabMembership, {"user_id": stored_user.id, "lab_id": lab_id}) if stored_user else None
    if not membership or membership.role != "lab_admin":
        raise HTTPException(status_code=403, detail="Lab administrator access required")
    return user


def require_lab_access(request: Request, lab_id: str, db: Session) -> dict | None:
    """Enforce Lab membership when OAuth is enabled; keep local demo mode open."""
    if request is None or not google_enabled():
        return None
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    if user.get("role") == "system_admin":
        return user
    stored_user = db.query(User).filter(User.email == (user.get("email") or "").lower()).first()
    membership = db.get(LabMembership, {"user_id": stored_user.id, "lab_id": lab_id}) if stored_user else None
    if not membership:
        raise HTTPException(status_code=403, detail="Lab membership required")
    return user


@router.get("/api/auth/google/start")
def google_login() -> RedirectResponse:
    if not google_enabled():
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    state = google_state()
    response = RedirectResponse(google_authorization_url(state), status_code=302)
    response.set_cookie("radar_oauth_state", state, httponly=True, secure=False, samesite="lax", max_age=600)
    return response


@router.get("/api/auth/google/callback")
def google_callback(code: str, state: str, request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    if state != request.cookies.get("radar_oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    try:
        user = exchange_google_code(code)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Google login failed") from error
    stored_user = sync_user(db, user)
    response = RedirectResponse(settings.frontend_url, status_code=302)
    cross_site = _cross_site_cookie()
    response.set_cookie(
        "radar_session",
        create_session(session_profile(stored_user)),
        httponly=True,
        secure=cross_site,
        samesite="none" if cross_site else "lax",
        max_age=60 * 60 * 24 * 7,
    )
    response.delete_cookie("radar_oauth_state", samesite="lax")
    return response


@router.get("/api/auth/me", response_model=AuthUserRead)
def auth_me(request: Request, db: Session = Depends(get_db)) -> AuthUserRead:
    user = _current_user(request)
    if not user:
        return AuthUserRead(authenticated=False, oauth_configured=google_enabled())
    stored_user = db.query(User).filter(User.email == (user.get("email") or "").lower()).first()
    memberships = stored_user.memberships if stored_user else []
    if user.get("role") == "system_admin":
        all_labs = db.query(Lab).order_by(Lab.name.asc()).all()
        lab_ids = [lab.id for lab in all_labs]
        lab_names = [lab.name for lab in all_labs]
    else:
        lab_ids = [item.lab_id for item in memberships]
        lab_names = [item.lab.name for item in memberships]
    return AuthUserRead(authenticated=True, email=user.get("email"), name=user.get("name"), picture=user.get("picture"), role=user.get("role", "guest"), oauth_configured=google_enabled(), lab_ids=lab_ids, lab_names=lab_names)


@router.post("/api/auth/logout")
def auth_logout(response: Response) -> dict[str, bool]:
    cross_site = _cross_site_cookie()
    response.delete_cookie("radar_session", secure=cross_site, samesite="none" if cross_site else "lax")
    return {"ok": True}


@router.delete("/api/auth/me/data", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_data(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    """Delete the signed-in user's account data without deleting shared Lab content."""
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    stored_user = db.query(User).filter(User.email == (user.get("email") or "").lower()).first()
    if stored_user is not None:
        db.query(LabAuditLog).filter(LabAuditLog.actor_user_id == stored_user.id).delete(synchronize_session=False)
        db.query(LabInvitation).filter(LabInvitation.invited_by == stored_user.id).update({LabInvitation.invited_by: None}, synchronize_session=False)
        db.delete(stored_user)
        db.commit()
    response.delete_cookie("radar_session")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


def _membership_read(membership: LabMembership) -> LabMembershipRead:
    return LabMembershipRead(user_id=membership.user_id, lab_id=membership.lab_id, lab_name=membership.lab.name, email=membership.user.email, name=membership.user.name, role=membership.role)


@router.get("/api/admin/memberships", response_model=list[LabMembershipRead])
def admin_memberships(db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> list[LabMembershipRead]:
    memberships = db.query(LabMembership).join(LabMembership.user).join(LabMembership.lab).order_by(LabMembership.created_at.desc()).all()
    return [_membership_read(membership) for membership in memberships]


@router.put("/api/admin/memberships/{user_id}/{lab_id}", response_model=LabMembershipRead)
def update_membership(user_id: str, lab_id: str, payload: LabMembershipUpdate, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> LabMembershipRead:
    if payload.role not in {"lab_admin", "lab_user"}:
        raise HTTPException(status_code=422, detail="Role must be lab_admin or lab_user")
    user = db.get(User, user_id)
    lab = db.get(Lab, lab_id)
    if user is None or lab is None:
        raise HTTPException(status_code=404, detail="User or lab not found")
    membership = db.get(LabMembership, {"user_id": user_id, "lab_id": lab_id})
    if membership is None:
        membership = LabMembership(user_id=user_id, lab_id=lab_id, role=payload.role)
        db.add(membership)
    else:
        membership.role = payload.role
    if user.role != "system_admin":
        user.role = payload.role
    db.commit()
    db.refresh(membership)
    return _membership_read(membership)


@router.get("/api/labs/{lab_id}/memberships", response_model=list[LabMembershipRead])
def lab_memberships(lab_id: str, request: Request, db: Session = Depends(get_db)) -> list[LabMembershipRead]:
    require_lab_admin(request, lab_id, db)
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    memberships = db.query(LabMembership).join(LabMembership.user).join(LabMembership.lab).filter(LabMembership.lab_id == lab_id).order_by(LabMembership.created_at.desc()).all()
    return [_membership_read(membership) for membership in memberships]


@router.put("/api/labs/{lab_id}/memberships/{user_id}", response_model=LabMembershipRead)
def update_lab_membership(lab_id: str, user_id: str, payload: LabMembershipUpdate, request: Request, db: Session = Depends(get_db)) -> LabMembershipRead:
    actor = require_lab_admin(request, lab_id, db)
    if payload.role not in {"lab_admin", "lab_user"}:
        raise HTTPException(status_code=422, detail="Role must be lab_admin or lab_user")
    user = db.get(User, user_id)
    lab = db.get(Lab, lab_id)
    if user is None or lab is None:
        raise HTTPException(status_code=404, detail="User or lab not found")
    membership = db.get(LabMembership, {"user_id": user_id, "lab_id": lab_id})
    if membership is None:
        membership = LabMembership(user_id=user_id, lab_id=lab_id, role=payload.role)
        db.add(membership)
    else:
        membership.role = payload.role
    if user.role != "system_admin":
        user.role = payload.role
    _audit_lab_action(db, lab_id, actor, "membership_role_changed", user.email, {"role": payload.role})
    db.commit()
    db.refresh(membership)
    return _membership_read(membership)


@router.get("/api/admin/invitations", response_model=list[LabInvitationRead])
def admin_invitations(db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> list[LabInvitationRead]:
    invitations = db.query(LabInvitation).join(LabInvitation.lab).order_by(LabInvitation.created_at.desc()).all()
    return [LabInvitationRead(id=item.id, email=item.email, lab_id=item.lab_id, lab_name=item.lab.name, role=item.role, status=item.status, created_at=item.created_at.isoformat()) for item in invitations]


@router.post("/api/admin/invitations", response_model=LabInvitationRead, status_code=status.HTTP_201_CREATED)
def create_invitation(payload: LabInvitationCreate, db: Session = Depends(get_db), admin: Optional[dict] = Depends(require_admin)) -> LabInvitationRead:
    email = payload.email.strip().lower()
    if "@" not in email or payload.role not in {"lab_admin", "lab_user"}:
        raise HTTPException(status_code=422, detail="Invalid email or role")
    lab = db.get(Lab, payload.lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    existing = db.query(LabInvitation).filter(LabInvitation.email == email, LabInvitation.lab_id == payload.lab_id, LabInvitation.status == "pending").first()
    if existing:
        existing.role = payload.role
        db.commit()
        db.refresh(existing)
        item = existing
    else:
        inviter = db.query(User).filter(User.email == (admin or {}).get("email", "").lower()).first()
        item = LabInvitation(id=f"invite-{secrets.token_urlsafe(12)}", email=email, lab_id=payload.lab_id, role=payload.role, invited_by=inviter.id if inviter else None)
        db.add(item)
        db.commit()
        db.refresh(item)
    return LabInvitationRead(id=item.id, email=item.email, lab_id=item.lab_id, lab_name=lab.name, role=item.role, status=item.status, created_at=item.created_at.isoformat())


@router.get("/api/labs/{lab_id}/invitations", response_model=list[LabInvitationRead])
def lab_invitations(lab_id: str, request: Request, db: Session = Depends(get_db)) -> list[LabInvitationRead]:
    require_lab_admin(request, lab_id, db)
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    invitations = db.query(LabInvitation).join(LabInvitation.lab).filter(LabInvitation.lab_id == lab_id).order_by(LabInvitation.created_at.desc()).all()
    return [LabInvitationRead(id=item.id, email=item.email, lab_id=item.lab_id, lab_name=item.lab.name, role=item.role, status=item.status, created_at=item.created_at.isoformat()) for item in invitations]


@router.post("/api/labs/{lab_id}/invitations", response_model=LabInvitationRead, status_code=status.HTTP_201_CREATED)
def create_lab_invitation(lab_id: str, payload: LabInvitationCreate, request: Request, db: Session = Depends(get_db)) -> LabInvitationRead:
    admin = require_lab_admin(request, lab_id, db)
    email = payload.email.strip().lower()
    if "@" not in email or payload.role not in {"lab_admin", "lab_user"}:
        raise HTTPException(status_code=422, detail="Invalid email or role")
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    existing = db.query(LabInvitation).filter(LabInvitation.email == email, LabInvitation.lab_id == lab_id, LabInvitation.status == "pending").first()
    if existing:
        existing.role = payload.role
        db.commit()
        db.refresh(existing)
        item = existing
    else:
        inviter = db.query(User).filter(User.email == (admin or {}).get("email", "").lower()).first()
        item = LabInvitation(id=f"invite-{secrets.token_urlsafe(12)}", email=email, lab_id=lab_id, role=payload.role, invited_by=inviter.id if inviter else None)
        db.add(item)
        db.commit()
        db.refresh(item)
    _audit_lab_action(db, lab_id, admin, "invitation_created", email, {"role": payload.role})
    db.commit()
    return LabInvitationRead(id=item.id, email=item.email, lab_id=item.lab_id, lab_name=lab.name, role=item.role, status=item.status, created_at=item.created_at.isoformat())


@router.get("/api/labs/{lab_id}/audit-logs", response_model=list[LabAuditLogRead])
def lab_audit_logs(lab_id: str, request: Request, db: Session = Depends(get_db)) -> list[LabAuditLogRead]:
    require_lab_admin(request, lab_id, db)
    entries = db.query(LabAuditLog).filter(LabAuditLog.lab_id == lab_id).order_by(LabAuditLog.created_at.desc()).limit(50).all()
    return [LabAuditLogRead(id=item.id, lab_id=item.lab_id, actor_name=item.actor.name if item.actor else None, actor_email=item.actor.email if item.actor else None, action=item.action, target=item.target, details=item.details, created_at=item.created_at) for item in entries]


def _lab_source_recommendation(lab: Lab, source: Source, watch_names: list[str]) -> tuple[bool, str]:
    profile = lab.profile
    profile_text = json.dumps({
        "description": lab.description,
        "research_scope": profile.research_scope if profile else {},
        "watchlist": profile.watchlist if profile else {},
        "signal_rules": profile.signal_rules if profile else {},
    }, ensure_ascii=False).casefold()
    source_tags = " ".join(str(tag) for tag in (source.raw_metadata or {}).get("recommendation_tags", []))
    source_text = f"{source.title} {source.source_type} {source.url or ''} {source_tags}".casefold()
    matched = [name for name in watch_names if len(name.strip()) >= 2 and name.casefold() in source_text]
    if matched:
        return True, f"匹配当前 Lab 的关注对象：{'、'.join(matched[:3])}。"
    if profile and source.source_type in {"paper_feed", "paper_api", "conference_article"}:
        return True, "适合补充当前 Lab 的公开论文、会议和研究资料。"
    if profile_text and source.source_type in {"news_feed", "company_news", "company_product"}:
        return True, "可补充企业和技术新闻，建议结合 Lab 关注对象启用。"
    return False, "系统来源目录中的可选来源，可按研究需要启用。"


def _lab_source_read(lab: Lab, source: Source, link: LabSource | None, watch_names: list[str]) -> LabSourceRead:
    docs = list(source.documents)
    source_format = (source.raw_metadata or {}).get("format")
    recommended, reason = _lab_source_recommendation(lab, source, watch_names)
    status_label = "已停用" if not source.enabled else ("异常" if source.last_error else ("有数据" if docs else ("需 API Key" if source_format == "patentsview" and not settings.patentsview_api_key else ("可抓取" if source.url and source_format else "未配置"))))
    return LabSourceRead(
        lab_id=lab.id,
        source_id=source.id,
        source_type=source.source_type,
        title=source.title,
        url=source.url,
        format=source_format,
        document_count=len(docs),
        status=status_label,
        source_enabled=source.enabled,
        enabled=bool(link and link.enabled),
        recommended=recommended,
        recommendation_reason=reason,
        last_error=source.last_error,
    )


@router.get("/api/labs/{lab_id}/sources", response_model=list[LabSourceRead])
def lab_sources(lab_id: str, request: Request, db: Session = Depends(get_db)) -> list[LabSourceRead]:
    require_lab_admin(request, lab_id, db)
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    links = {link.source_id: link for link in db.query(LabSource).filter(LabSource.lab_id == lab_id).all()}
    watch_names = [item.watch_item.name for item in db.query(LabWatchItem).join(LabWatchItem.watch_item).filter(LabWatchItem.lab_id == lab_id).all()]
    sources = [source for source in db.scalars(select(Source).options(selectinload(Source.documents)).order_by(Source.title.asc())).all() if source.enabled]
    return [_lab_source_read(lab, source, links.get(source.id), watch_names) for source in sources]


@router.put("/api/labs/{lab_id}/sources/{source_id}", response_model=LabSourceRead)
def update_lab_source(lab_id: str, source_id: str, payload: LabSourceUpdate, request: Request, db: Session = Depends(get_db)) -> LabSourceRead:
    actor = require_lab_admin(request, lab_id, db)
    lab = db.get(Lab, lab_id)
    source = db.get(Source, source_id)
    if lab is None or source is None:
        raise HTTPException(status_code=404, detail="Lab or source not found")
    if payload.enabled and not source.enabled:
        if actor.get("role") != "system_admin":
            raise HTTPException(status_code=409, detail="Source requires system administrator approval")
        source.enabled = True
    link = db.get(LabSource, {"lab_id": lab_id, "source_id": source_id})
    if link is None:
        link = LabSource(lab_id=lab_id, source_id=source_id, enabled=payload.enabled)
        db.add(link)
    else:
        link.enabled = payload.enabled
    db.commit()
    db.refresh(link)
    watch_names = [item.watch_item.name for item in db.query(LabWatchItem).join(LabWatchItem.watch_item).filter(LabWatchItem.lab_id == lab_id).all()]
    source.documents = list(db.scalars(select(Document).where(Document.source_id == source_id)).all())
    return _lab_source_read(lab, source, link, watch_names)


@router.post("/api/labs/{lab_id}/sources/batch", response_model=list[LabSourceRead])
def add_lab_sources_batch(lab_id: str, payload: LabSourceBatchUpdate, request: Request, db: Session = Depends(get_db)) -> list[LabSourceRead]:
    actor = require_lab_admin(request, lab_id, db)
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    source_ids = list(dict.fromkeys(payload.source_ids))
    sources = db.query(Source).filter(Source.id.in_(source_ids)).all() if source_ids else []
    if len(sources) != len(source_ids):
        raise HTTPException(status_code=404, detail="One or more sources not found")
    for source in sources:
        if not source.enabled:
            if actor.get("role") != "system_admin":
                raise HTTPException(status_code=409, detail="Source requires system administrator approval")
            source.enabled = True
        link = db.get(LabSource, {"lab_id": lab_id, "source_id": source.id})
        if link is None:
            db.add(LabSource(lab_id=lab_id, source_id=source.id, enabled=True))
        else:
            link.enabled = True
    db.commit()
    watch_names = [item.watch_item.name for item in db.query(LabWatchItem).join(LabWatchItem.watch_item).filter(LabWatchItem.lab_id == lab_id).all()]
    result = []
    for source in sources:
        source.documents = list(db.scalars(select(Document).where(Document.source_id == source.id)).all())
        result.append(_lab_source_read(lab, source, db.get(LabSource, {"lab_id": lab_id, "source_id": source.id}), watch_names))
    return result


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health")
def api_health() -> dict[str, str]:
    """Stable liveness endpoint for reverse proxies and deployment monitors."""
    return {"status": "ok"}


def _check_postgres() -> str:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()
    return "ok"


def _check_redis() -> str:
    client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        client.ping()
    finally:
        client.close()
    return "ok"


def _check_minio() -> str:
    scheme = "https" if settings.minio_secure else "http"
    url = f"{scheme}://{settings.minio_endpoint}/minio/health/live"
    with urlopen(url, timeout=2) as response:
        if response.status >= 400:
            raise URLError(f"MinIO health check failed with status {response.status}")
    return "ok"


@router.get("/health/ready")
def readiness(response: Response) -> dict[str, object]:
    checks = {
        "api": "ok",
        "postgres": "unknown",
        "redis": "unknown",
        "minio": "unknown",
    }

    for name, check in (
        ("postgres", _check_postgres),
        ("redis", _check_redis),
        ("minio", _check_minio),
    ):
        try:
            checks[name] = check()
        except Exception:
            checks[name] = "unavailable"

    ready = all(value == "ok" for value in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {"status": "ok" if ready else "degraded", "checks": checks}


@router.get("/api/version")
def version() -> dict[str, str]:
    return {"name": "research-radar-api", "version": "0.1.0"}


@router.get("/api/ai/status")
def ai_status() -> dict[str, object]:
    provider = active_provider()
    assistant_provider = active_provider(purpose="assistant")
    return {"configured": provider != "rule_based", "provider": provider, "model": active_model(provider), "assistant_provider": assistant_provider, "assistant_model": active_model(assistant_provider), "web_search_enabled": settings.openai_ai_search_enabled, "assistant_web_search_enabled": settings.assistant_web_search_enabled}


@router.get("/api/ai/dify/check")
def dify_check() -> dict[str, object]:
    return check_dify_connection()


def _affected_labs(change: Change) -> list[str]:
    return [interpretation.lab.name for interpretation in change.interpretations if interpretation.lab]


def _to_change_card(change: Change, watch_item_names: dict[str, str] | None = None, published_at: datetime | None = None) -> ChangeCard:
    watch_items = [watch_item_names.get(item_id, item_id) for item_id in (change.watch_item_ids or [])] if watch_item_names else (change.watch_item_ids or [])
    return ChangeCard(
        id=change.id,
        title=change.title,
        new_facts=change.new_facts,
        change_summary=change.change_summary,
        previous_state=change.previous_state,
        current_state=change.current_state,
        importance=change.importance,
        evidence=change.evidence,
        next_watch_points=change.next_watch_points,
        affected_labs=_affected_labs(change),
        watch_items=watch_items,
        detected_at=change.detected_at,
        published_at=published_at,
    )


def _to_lab_change_card(interpretation: LabChangeInterpretation, watch_item_names: dict[str, str] | None = None, published_at: datetime | None = None) -> LabChangeCard:
    change = interpretation.change
    return LabChangeCard(
        **_to_change_card(change, watch_item_names, published_at).model_dump(),
        why_relevant=interpretation.why_relevant,
        impact=interpretation.impact,
        lab_next_watch_points=interpretation.next_watch_points,
        ai_generated=interpretation.generation_method == "ai",
        ai_provider=(interpretation.change.evidence[0].get("ai_provider") if interpretation.change.evidence and isinstance(interpretation.change.evidence[0], dict) else None) or ("ai" if interpretation.generation_method == "ai" else "rule_based"),
    )


def _today_start() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _change_published_at(db: Session, change: Change) -> datetime | None:
    dates: list[datetime] = []
    for item in change.evidence or []:
        if not isinstance(item, dict) or not item.get("document_id"):
            continue
        document = db.get(Document, item["document_id"])
        if document and document.published_at:
            value = document.published_at
            dates.append(value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value)
    return max(dates) if dates else None


def _changes_by_published_window(db: Session, start: datetime, end: datetime) -> list[Change]:
    candidates = db.scalars(select(Change).options(selectinload(Change.interpretations).selectinload(LabChangeInterpretation.lab))).all()
    selected = [change for change in candidates if (published := _change_published_at(db, change)) and start <= published < end]
    selected.sort(key=lambda change: (_importance_order_value(change.importance), _change_published_at(db, change) or start), reverse=False)
    return selected


def _importance_order_value(value: str) -> int:
    return {"S": 0, "A": 1, "B": 2, "C": 3}.get(value, 4)


def _importance_order():
    return case(
        (Change.importance == "S", 0),
        (Change.importance == "A", 1),
        (Change.importance == "B", 2),
        (Change.importance == "C", 3),
        else_=4,
    )


@router.get("/api/changes/today", response_model=list[ChangeCard])
def today_changes(db: Session = Depends(get_db)) -> list[ChangeCard]:
    today = _today_start()
    changes = _changes_by_published_window(db, today, today + timedelta(days=1))
    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return [_to_change_card(change, watch_item_names, _change_published_at(db, change)) for change in changes]


@router.get("/api/changes/week", response_model=list[ChangeCard])
def week_changes(db: Session = Depends(get_db)) -> list[ChangeCard]:
    today = _today_start()
    week_start = today - timedelta(days=today.weekday())
    changes = _changes_by_published_window(db, week_start, today + timedelta(days=1))
    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return [_to_change_card(change, watch_item_names, _change_published_at(db, change)) for change in changes]


@router.get("/api/changes/month", response_model=list[ChangeCard])
def month_changes(db: Session = Depends(get_db)) -> list[ChangeCard]:
    today = _today_start()
    month_start = today.replace(day=1)
    changes = _changes_by_published_window(db, month_start, today)
    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return [_to_change_card(change, watch_item_names, _change_published_at(db, change)) for change in changes]


@router.get("/api/labs", response_model=list[LabRead])
def labs(db: Session = Depends(get_db)) -> list[LabRead]:
    return [
        _lab_read(lab)
        for lab in db.scalars(select(Lab).order_by(Lab.name.asc())).all()
    ]


@router.get("/api/labs/{lab_id}", response_model=LabRead)
def lab_detail(lab_id: str, request: Request, db: Session = Depends(get_db)) -> LabRead:
    require_lab_access(request, lab_id, db)
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    return _lab_read(lab)


@router.get("/api/labs/{lab_id}/profile", response_model=LabProfileRead)
def lab_profile(lab_id: str, request: Request, db: Session = Depends(get_db)) -> LabProfileRead:
    require_lab_access(request, lab_id, db)
    profile = db.get(LabProfile, lab_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Lab profile not found")
    return LabProfileRead(lab_id=lab_id, research_scope=profile.research_scope, watchlist=profile.watchlist, key_questions=profile.key_questions, signal_rules=profile.signal_rules, ai_policy=profile.ai_policy, update_frequency=profile.update_frequency)


@router.put("/api/labs/{lab_id}/profile", response_model=LabProfileRead)
def update_lab_profile(lab_id: str, payload: LabProfileUpdate, request: Request, db: Session = Depends(get_db)) -> LabProfileRead:
    require_lab_admin(request, lab_id, db)
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    if len(payload.key_questions) > 50 or len(payload.signal_rules.get("keywords", [])) > 200:
        raise HTTPException(status_code=422, detail="Lab profile is too large")
    profile = db.get(LabProfile, lab_id)
    if profile is None:
        profile = LabProfile(lab_id=lab_id)
        db.add(profile)
    profile.research_scope = payload.research_scope
    profile.watchlist = payload.watchlist
    profile.key_questions = payload.key_questions
    profile.signal_rules = payload.signal_rules
    profile.ai_policy = payload.ai_policy
    profile.update_frequency = payload.update_frequency
    db.commit()
    db.refresh(profile)
    return LabProfileRead(lab_id=lab_id, research_scope=profile.research_scope, watchlist=profile.watchlist, key_questions=profile.key_questions, signal_rules=profile.signal_rules, ai_policy=profile.ai_policy, update_frequency=profile.update_frequency)


@router.post("/api/labs/{lab_id}/assistant")
def lab_assistant(lab_id: str, payload: AssistantAsk, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Snowy uses controlled research tools so the model can be switched without changing Lab logic."""
    require_lab_access(request, lab_id, db)
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")

    watch_items = [link.watch_item.name for link in db.query(LabWatchItem).filter(LabWatchItem.lab_id == lab_id).all()]
    profile = lab.profile
    sources: list[dict[str, Any]] = []
    web_search_used = False

    def _evidence_dict(value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            dumped = value.model_dump()
            return dumped if isinstance(dumped, dict) else {}
        return value if isinstance(value, dict) else {}

    def _change_payload(change: LabChangeCard) -> dict[str, Any]:
        evidence = _evidence_dict(change.evidence[0]) if change.evidence else {}
        existing = next((source for source in sources if source.get("url") == evidence.get("url") and source.get("title") == (evidence.get("source_title") or change.title)), None)
        if existing is None:
            existing = {"index": len(sources) + 1, "title": evidence.get("source_title") or change.title, "url": evidence.get("url")}
            sources.append(existing)
        return {"source_index": existing["index"], "change_id": change.id, "title": change.title, "summary": change.change_summary, "facts": change.new_facts[:3], "why_relevant": change.why_relevant, "impact": change.impact, "importance": change.importance}

    def execute_tool(name: str, arguments: dict[str, Any]) -> Any:
        if name == "get_lab_profile":
            return {"lab_name": lab.name, "description": lab.description or "", "research_scope": profile.research_scope if profile else {}, "watchlist": profile.watchlist if profile else {}, "key_questions": profile.key_questions if profile else [], "followed_items": watch_items}
        if name == "get_today_changes":
            return {"date_scope": "today", "changes": [_change_payload(change) for change in lab_today_changes(lab_id, None, db)]}
        if name == "search_lab_articles":
            query = str(arguments.get("query", "")).strip().casefold()
            if not query:
                return {"error": "query is required"}
            matches = []
            for change in lab_month_changes(lab_id, None, db):
                haystack = " ".join([change.title, change.change_summary, change.why_relevant, change.impact, *change.watch_items]).casefold()
                if all(term in haystack for term in query.split()):
                    matches.append(_change_payload(change))
            return {"query": query, "matches": matches[:8]}
        if name == "get_change_evidence":
            change_id = str(arguments.get("change_id", ""))
            for change in [*lab_today_changes(lab_id, None, db), *lab_month_changes(lab_id, None, db)]:
                if change.id == change_id:
                    return {"change": _change_payload(change), "evidence": [_evidence_dict(item) for item in change.evidence], "next_watch_points": change.next_watch_points}
            return {"error": "change not found for this Lab"}
        if name == "search_public_web":
            nonlocal web_search_used
            if not settings.assistant_web_search_enabled:
                return {"error": "Public web search is disabled for this assistant."}
            query = str(arguments.get("query", "")).strip()
            try:
                results = search_public_web(query, limit=5)
            except Exception:
                return {"error": "Public web search is temporarily unavailable."}
            web_search_used = bool(results) or web_search_used
            formatted = []
            for item in results:
                existing = next((source for source in sources if source.get("url") == item["url"]), None)
                if existing is None:
                    existing = {"index": len(sources) + 1, "title": item["title"], "url": item["url"]}
                    sources.append(existing)
                formatted.append({"source_index": existing["index"], **item})
            return {"query": query, "results": formatted}
        return {"error": f"unknown tool: {name}"}

    tools = [
        {"type": "function", "function": {"name": "get_lab_profile", "description": "Read this Lab's research scope, watchlist, key questions and followed items.", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}},
        {"type": "function", "function": {"name": "get_today_changes", "description": "Read the Lab changes published today. Use this before making a daily judgment.", "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}},
        {"type": "function", "function": {"name": "search_lab_articles", "description": "Search this Lab's current-month changes by topic, company, person or technical phrase.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}}},
        {"type": "function", "function": {"name": "get_change_evidence", "description": "Read the source evidence and next watch points for one Lab change.", "parameters": {"type": "object", "properties": {"change_id": {"type": "string"}}, "required": ["change_id"], "additionalProperties": False}}},
        {"type": "function", "function": {"name": "search_public_web", "description": "Search the public web for current information not covered by this Lab's stored sources. Use only when the question needs external or latest information.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}}},
    ]

    question = payload.question.strip()
    response_language = "English" if payload.locale == "en" else "Japanese" if payload.locale == "ja" else "Chinese"
    history = [
        {"role": item.get("role", ""), "content": item.get("content", "").strip()[:4000]}
        for item in payload.history
        if item.get("role") in {"user", "assistant"} and item.get("content", "").strip()
    ][-10:]
    article_context = payload.context.strip()
    if history:
        transcript = "\n".join(f"{item['role']}: {item['content']}" for item in history)
        user_request = f"This is a follow-up in the same conversation. Use the conversation history to resolve references such as '上面那篇文章' or '你刚才说的'.\nConversation history:\n{transcript}\n\nLatest user message: {question}"
    else:
        user_request = "The user just opened the assistant. Learn the Lab profile and today's changes, then briefly explain what you learned and what they can ask next." if not question else question
    if article_context:
        user_request += f"\n\nArticle context for this request:\n{article_context}"
    language_rule = {
        "English": "Write every user-facing field in English only. Do not use Chinese or Japanese characters, even when the source material is Chinese.",
        "Japanese": "Write every user-facing field in Japanese only. Do not use Chinese or English prose, except proper nouns, product names, URLs, and technical acronyms.",
        "Chinese": "请将所有面向用户的字段统一使用简体中文。除专有名词、产品名、URL 和技术缩写外，不要使用英文或日文句子。",
    }[response_language]
    system_prompt = f"""You are Snowy, a warm but rigorous research assistant for {lab.name}.
Use the provided research tools before answering. When conversation history is present, continue that conversation instead of restarting with a generic Lab overview. Resolve references to earlier messages and articles using the history and tools. You may search the public web when the Lab sources do not cover the question or when the user asks for current external information. Do not invent facts or claim to have read anything that a tool did not return. Treat source facts and your inference separately. Every conclusion must cite one or more source_index values from tool results. If there are no today's changes, say so clearly.
Language requirement: {language_rule}

Return ONLY valid JSON with this shape:
{json.dumps(ASSISTANT_SCHEMA, ensure_ascii=False)}
The answer and all user-facing fields must be concise {response_language}. studied_articles should contain article titles, conclusions should be decision-relevant, uncertainties should be explicit, and suggested_questions should be useful follow-ups."""
    try:
        final_text, provider = call_chat_agent(system_prompt, user_request, tools, execute_tool)
        cleaned = final_text.strip().replace("```json", "").replace("```JSON", "").replace("```", "").strip()
        try:
            result = parse_json_object(cleaned)
        except (AIUnavailableError, json.JSONDecodeError):
            # Never render a malformed JSON envelope as the user's answer.
            # Recover its useful fields first; only keep raw text when it is
            # clearly a normal non-JSON response.
            try:
                result = salvage_json_object(cleaned)
            except AIUnavailableError:
                result = {"answer": "DeepSeek 返回了无法解析的结构化结果，我已保留这次对话，但暂时不能可靠总结。请重新提问一次。" if cleaned.lstrip().startswith("{") else cleaned}
        if not isinstance(result, dict):
            result = {"answer": str(result)}
        result = _normalize_assistant_result(result)
        result["source_indexes"] = [int(index) for index in result.get("source_indexes", []) if 1 <= int(index) <= len(sources)]
        result["provider"] = provider
        result["answer_source"] = "deepseek_agent" if provider == "deepseek" else f"{provider}_agent"
        result["degraded"] = False
        result["web_search_used"] = web_search_used
    except (AIUnavailableError, KeyError, TypeError, ValueError) as error:
        logger.warning("Snowy assistant fell back to local rules for lab %s: %s", lab_id, error)
        today_context = execute_tool("get_today_changes", {})
        titles = [item["title"] for item in today_context["changes"]]
        fallback_copy = {
            "English": {
                "answer": f"DeepSeek did not return a result. I reviewed the local research data for {lab.name}, which currently contains {len(titles)} relevant signals.",
                "summary": f"Read the Lab profile, {len(titles)} current changes, and {len(watch_items)} followed items.",
                "uncertainty": "This is based only on collected public materials and needs further independent validation.",
                "suggestions": ["What is the most important change this week?", "Which conclusions need more evidence?", "What should we track next?"],
                "empty": "There are no new Lab-related changes today.",
            },
            "Japanese": {
                "answer": f"DeepSeekから結果が返りませんでした。{lab.name}の収集済み研究データを確認しました。現在、関連シグナルは{len(titles)}件です。",
                "summary": f"Labプロフィール、現在の変化{len(titles)}件、フォロー項目{len(watch_items)}件を確認しました。",
                "uncertainty": "収集済みの公開資料のみに基づくため、追加の独立検証が必要です。",
                "suggestions": ["今週最も重要な変化は何ですか？", "どの結論に追加の証拠が必要ですか？", "次に何を追跡すべきですか？"],
                "empty": "本日、新しいLab関連の変化はありません。",
            },
            "Chinese": {
                "answer": f"DeepSeek 暂时没有返回结果。我先用本地已采集数据了解了 {lab.name} 的研究范围和 {len(titles)} 条相关变化。",
                "summary": f"已读取 Lab Profile、{len(titles)} 条当前变化和 {len(watch_items)} 个关注项。",
                "uncertainty": "当前仅基于已采集的公开资料，不能替代工程或客户验证。",
                "suggestions": ["这周最值得关注的变化是什么？", "哪些判断还缺少证据？", "接下来应该继续追踪什么？"],
                "empty": "今天暂无新的 Lab 相关变化。",
            },
        }[response_language]
        result = {
            "answer": fallback_copy["answer"] if not question else fallback_copy["answer"],
            "learning_summary": fallback_copy["summary"],
            "conclusions": [item["impact"] for item in today_context["changes"][:3]] or [fallback_copy["empty"]],
            "studied_articles": titles,
            "uncertainties": [fallback_copy["uncertainty"]],
            "suggested_questions": fallback_copy["suggestions"],
            "source_indexes": list(range(1, min(len(sources), 3) + 1)),
            "provider": "rule_based",
            "answer_source": "rule_based_fallback",
            "degraded": True,
            "web_search_used": web_search_used,
        }
    return {**result, "assistant": "Snowy", "lab_id": lab_id, "lab_name": lab.name, "studied_count": len(sources), "sources": sources}


def _lab_read(lab: Lab) -> LabRead:
    admin = next((membership for membership in lab.memberships if membership.role == "lab_admin"), None)
    pending_admin = next((invitation for invitation in lab.invitations if invitation.role == "lab_admin" and invitation.status == "pending"), None) if hasattr(lab, "invitations") else None
    return LabRead(id=lab.id, name=lab.name, description=lab.description, admin_email=admin.user.email if admin else (pending_admin.email if pending_admin else None), admin_name=admin.user.name if admin else None)


def _assign_lab_admin(db: Session, lab: Lab, email: Optional[str]) -> None:
    if email is None:
        return
    normalized = email.strip().lower()
    if not normalized or "@" not in normalized:
        raise HTTPException(status_code=422, detail="Valid administrator email is required")
    existing_admins = db.query(LabMembership).filter(LabMembership.lab_id == lab.id, LabMembership.role == "lab_admin").all()
    for membership in existing_admins:
        membership.role = "lab_user"
    user = db.query(User).filter(User.email == normalized).first()
    if user:
        membership = db.get(LabMembership, {"user_id": user.id, "lab_id": lab.id})
        if membership is None:
            db.add(LabMembership(user_id=user.id, lab_id=lab.id, role="lab_admin"))
        else:
            membership.role = "lab_admin"
        if user.role != "system_admin":
            user.role = "lab_admin"
    else:
        pending = db.query(LabInvitation).filter(LabInvitation.email == normalized, LabInvitation.lab_id == lab.id, LabInvitation.status == "pending").first()
        if pending:
            pending.role = "lab_admin"
        else:
            db.add(LabInvitation(id=f"invite-{secrets.token_urlsafe(12)}", email=normalized, lab_id=lab.id, role="lab_admin", status="pending"))


@router.post("/api/admin/labs", response_model=LabRead, status_code=status.HTTP_201_CREATED)
def create_lab(payload: LabCreate, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> LabRead:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Lab name is required")
    lab_id = "lab-" + "-".join(part for part in name.lower().replace("/", " ").split() if part)
    if db.get(Lab, lab_id):
        raise HTTPException(status_code=409, detail="Lab already exists")
    lab = Lab(id=lab_id, name=name, description=payload.description.strip() if payload.description else None)
    db.add(lab)
    db.flush()
    _assign_lab_admin(db, lab, payload.admin_email)
    db.commit()
    db.refresh(lab)
    return _lab_read(lab)


@router.put("/api/admin/labs/{lab_id}", response_model=LabRead)
def update_lab(lab_id: str, payload: LabUpdate, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> LabRead:
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    if payload.name is not None and not payload.name.strip():
        raise HTTPException(status_code=422, detail="Lab name is required")
    if payload.name is not None:
        lab.name = payload.name.strip()
    if payload.description is not None:
        lab.description = payload.description.strip()
    _assign_lab_admin(db, lab, payload.admin_email)
    db.commit()
    db.refresh(lab)
    return _lab_read(lab)


@router.delete("/api/admin/labs/{lab_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lab(lab_id: str, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> Response:
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    db.query(LabChangeInterpretation).filter(LabChangeInterpretation.lab_id == lab_id).delete(synchronize_session=False)
    db.query(LabMembership).filter(LabMembership.lab_id == lab_id).delete(synchronize_session=False)
    db.query(LabInvitation).filter(LabInvitation.lab_id == lab_id).delete(synchronize_session=False)
    db.query(LabWatchItem).filter(LabWatchItem.lab_id == lab_id).delete(synchronize_session=False)
    db.query(LabProfile).filter(LabProfile.lab_id == lab_id).delete(synchronize_session=False)
    db.delete(lab)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _lab_watch_item_read(item: WatchItem) -> LabWatchItemRead:
    return LabWatchItemRead(id=item.id, kind=item.kind, name=item.name, description=item.description, is_following=item.is_following, created_at=item.created_at)


@router.get("/api/labs/{lab_id}/watch-items", response_model=list[LabWatchItemRead])
def lab_watch_items(lab_id: str, request: Request, db: Session = Depends(get_db)) -> list[LabWatchItemRead]:
    require_lab_access(request, lab_id, db)
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    links = db.query(LabWatchItem).filter(LabWatchItem.lab_id == lab_id).all()
    if links:
        return [_lab_watch_item_read(link.watch_item) for link in links]
    return []


@router.get("/api/labs/{lab_id}/watch-items/{watch_item_id}/articles", response_model=list[WatchArticleRead])
def lab_watch_item_articles(lab_id: str, watch_item_id: str, request: Request, db: Session = Depends(get_db)) -> list[WatchArticleRead]:
    require_lab_access(request, lab_id, db)
    link = db.get(LabWatchItem, {"lab_id": lab_id, "watch_item_id": watch_item_id})
    if link is None:
        raise HTTPException(status_code=404, detail="关注对象不属于当前 Lab")
    selected_sources = [row.source_id for row in db.query(LabSource).filter(LabSource.lab_id == lab_id, LabSource.enabled.is_(True)).all()]
    query = select(Document).options(selectinload(Document.source), selectinload(Document.analysis)).where(
        or_(Document.title.ilike(f"%{link.watch_item.name}%"), Document.content_text.ilike(f"%{link.watch_item.name}%"))
    )
    if selected_sources:
        query = query.where(Document.source_id.in_(selected_sources))
    documents = db.scalars(query.order_by(Document.published_at.desc(), Document.fetched_at.desc()).limit(8)).all()
    if not documents:
        try:
            search_watch_item(db, link.lab, link.watch_item)
        except Exception as error:
            logger.warning("Watch item web search failed for %s: %s", watch_item_id, error)
        documents = db.scalars(query.order_by(Document.published_at.desc(), Document.fetched_at.desc()).limit(8)).all()
    results: list[WatchArticleRead] = []
    for document in documents:
        summary = document.analysis.summary if document.analysis and document.analysis.summary else " ".join(document.content_text.split())[:260]
        host = urlparse(document.canonical_url).netloc
        image_url = (document.raw_metadata or {}).get("image_url") or (f"https://www.google.com/s2/favicons?domain={host}&sz=128" if host else None)
        results.append(WatchArticleRead(id=document.id, title=document.title, summary=summary, url=document.canonical_url, image_url=image_url, published_at=document.published_at, source_title=document.source.title, source_type=document.source.source_type))
    return results


@router.post("/api/labs/{lab_id}/watch-items", response_model=LabWatchItemRead, status_code=status.HTTP_201_CREATED)
def add_lab_watch_item(lab_id: str, payload: LabWatchItemCreate, request: Request, db: Session = Depends(get_db)) -> LabWatchItemRead:
    require_lab_admin(request, lab_id, db)
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    name = payload.name.strip()
    if not name or payload.kind not in {"company", "university", "professor", "topic", "conference"}:
        raise HTTPException(status_code=422, detail="Invalid watch item")
    item = db.query(WatchItem).filter(WatchItem.kind == payload.kind, WatchItem.name == name).first()
    if item is None:
        item = WatchItem(id=f"{payload.kind}-{name.lower().replace(' ', '-')}", kind=payload.kind, name=name, description=payload.description, is_following=True)
        db.add(item)
        db.flush()
    if db.get(LabWatchItem, {"lab_id": lab_id, "watch_item_id": item.id}) is None:
        db.add(LabWatchItem(lab_id=lab_id, watch_item_id=item.id))
    db.commit()
    db.refresh(item)
    return _lab_watch_item_read(item)


@router.delete("/api/labs/{lab_id}/watch-items/{watch_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_lab_watch_item(lab_id: str, watch_item_id: str, request: Request, db: Session = Depends(get_db)) -> Response:
    require_lab_admin(request, lab_id, db)
    link = db.get(LabWatchItem, {"lab_id": lab_id, "watch_item_id": watch_item_id})
    if link:
        db.delete(link)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/watch-items", response_model=list[WatchItemRead])
def watch_items(db: Session = Depends(get_db)) -> list[WatchItemRead]:
    return list(db.scalars(select(WatchItem).order_by(WatchItem.kind.asc(), WatchItem.name.asc())).all())


@router.post("/api/watch-items", response_model=WatchItemRead, status_code=status.HTTP_201_CREATED)
def create_watch_item(payload: WatchItemCreate, db: Session = Depends(get_db)) -> WatchItemRead:
    item = WatchItem(
        id=f"{payload.kind}-{payload.name.lower().replace(' ', '-')}",
        kind=payload.kind,
        name=payload.name,
        description=payload.description,
        is_following=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/api/documents/recent", response_model=list[DocumentRead])
def recent_documents(db: Session = Depends(get_db)) -> list[DocumentRead]:
    documents = db.scalars(select(Document).options(selectinload(Document.source)).order_by(Document.fetched_at.desc()).limit(50)).all()
    return [_to_document_read(document) for document in documents]


@router.get("/api/admin/sources", response_model=list[SourceRead])
def admin_sources(db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> list[SourceRead]:
    result = []
    for source in db.scalars(select(Source).options(selectinload(Source.documents)).order_by(Source.title.asc())).all():
        result.append(_to_source_read(source))
    return result


@router.get("/api/admin/source-recommendations", response_model=list[SourceRecommendationRead])
def admin_source_recommendations(db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> list[SourceRecommendationRead]:
    labs = db.scalars(select(Lab).options(selectinload(Lab.profile)).order_by(Lab.name.asc())).all()
    sources = db.scalars(select(Source).order_by(Source.title.asc())).all()
    recommendations: list[SourceRecommendationRead] = []
    for lab in labs:
        watch_names = [item.watch_item.name for item in db.query(LabWatchItem).join(LabWatchItem.watch_item).filter(LabWatchItem.lab_id == lab.id).all()]
        profile = lab.profile
        profile_text = json.dumps({
            "description": lab.description,
            "research_scope": profile.research_scope if profile else {},
            "watchlist": profile.watchlist if profile else {},
            "signal_rules": profile.signal_rules if profile else {},
        }, ensure_ascii=False).casefold()
        selected = {link.source_id for link in db.query(LabSource).filter(LabSource.lab_id == lab.id, LabSource.enabled.is_(True)).all()}
        ranked: list[tuple[float, Source, str]] = []
        for source in sources:
            tags = [str(tag) for tag in (source.raw_metadata or {}).get("recommendation_tags", [])]
            source_text = f"{source.title} {source.source_type} {' '.join(tags)}".casefold()
            matched_watch = [name for name in watch_names if len(name.strip()) >= 2 and name.casefold() in source_text]
            matched_profile = [tag for tag in tags if tag.casefold() in profile_text]
            score = min(0.99, 0.35 + len(matched_watch) * 0.18 + len(matched_profile) * 0.08)
            if source.source_type in {"paper_feed", "paper_api", "news_feed", "company_news", "company_product", "patent_feed", "patent_api", "conference_article"}:
                score += 0.06
            if matched_watch or matched_profile or source.source_type in {"paper_feed", "paper_api", "news_feed", "company_news", "company_product", "patent_feed", "patent_api", "conference_article"}:
                reason = f"匹配关注对象：{'、'.join(matched_watch[:3])}。" if matched_watch else f"匹配研究方向：{'、'.join(matched_profile[:3]) or '公开研究资料'}。"
                ranked.append((min(score, 0.99), source, reason))
        ordered_ranked = sorted(ranked, key=lambda item: (-item[0], item[1].title))
        diverse: list[tuple[float, Source, str]] = []
        covered_types: set[str] = set()
        for item in ordered_ranked:
            source_type = item[1].source_type
            if source_type not in covered_types:
                diverse.append(item)
                covered_types.add(source_type)
        diverse.extend(item for item in ordered_ranked if item not in diverse)
        for score, source, reason in diverse[:30]:
            source_format = (source.raw_metadata or {}).get("format")
            recommendations.append(SourceRecommendationRead(
                lab_id=lab.id,
                lab_name=lab.name,
                source_id=source.id,
                title=source.title,
                source_type=source.source_type,
                url=source.url,
                format=source_format,
                score=round(score, 2),
                reason=reason,
                enabled=source.id in selected,
                source_enabled=source.enabled,
                requires_api_key=source_format == "patentsview",
            ))
    return recommendations


def _to_source_read(source: Source) -> SourceRead:
    docs = list(source.documents)
    published = [document.published_at for document in docs if document.published_at]
    fetched = [document.fetched_at for document in docs if document.fetched_at]
    source_format = (source.raw_metadata or {}).get("format")
    status_label = "已停用" if not source.enabled else ("异常" if source.last_error else ("有数据" if docs else ("需 API Key" if source_format == "patentsview" and not settings.patentsview_api_key else ("可抓取" if source.url and source_format else "未配置"))))
    return SourceRead(id=source.id, source_type=source.source_type, title=source.title, url=source.url, format=source_format, document_count=len(docs), latest_published_at=max(published) if published else None, latest_fetched_at=max(fetched) if fetched else None, status=status_label, enabled=source.enabled, last_error=source.last_error, last_checked_at=source.last_checked_at)


@router.put("/api/admin/sources/{source_id}/enabled", response_model=SourceRead)
def set_source_enabled(source_id: str, enabled: bool, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> SourceRead:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    source.enabled = enabled
    db.commit()
    db.refresh(source)
    source.documents = list(db.scalars(select(Document).where(Document.source_id == source_id)).all())
    return _to_source_read(source)


@router.post("/api/admin/sources/{source_id}/run", response_model=IngestResult)
def run_single_source(source_id: str, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> IngestResult:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.enabled:
        raise HTTPException(status_code=409, detail="Source is disabled")
    result = ingest_source(db, source)
    source.last_checked_at = utc_now()
    source.last_error = result.get("error")
    db.commit()
    return IngestResult(source_id=source.id, source_title=source.title, **result)


@router.post("/api/admin/sources/{source_id}/test")
def test_source(source_id: str, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> dict[str, object]:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    if not source.url:
        return {"ok": False, "status": "skipped", "error": "source has no URL", "message": "该来源没有配置地址。"}
    format_name = (source.raw_metadata or {}).get("format")
    if format_name == "patentsview" and not settings.patentsview_api_key:
        return {"ok": False, "status": "skipped", "error": "PATENTSVIEW_API_KEY is not configured", "message": "PatentsView 需要配置 API Key。"}
    try:
        headers = {"X-Api-Key": settings.patentsview_api_key} if format_name == "patentsview" and settings.patentsview_api_key else None
        _, content_type = fetch_url(source.url, headers)
        source.last_checked_at = utc_now()
        source.last_error = None
        db.commit()
        return {"ok": True, "status": "ok", "error": None, "content_type": content_type, "message": "连接成功，未写入资料。"}
    except Exception as error:
        source.last_checked_at = utc_now()
        source.last_error = str(error)
        db.commit()
        return {"ok": False, "status": "error", "error": str(error), "message": "连接失败，请检查地址或认证配置。"}


@router.delete("/api/admin/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: str, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> Response:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    documents = db.scalars(select(Document).where(Document.source_id == source_id)).all()
    document_ids = {document.id for document in documents}
    changes = db.scalars(select(Change)).all()
    change_ids = {change.id for change in changes if any(isinstance(item, dict) and item.get("source_id") == source_id for item in (change.evidence or []))}
    if change_ids:
        db.query(LabChangeInterpretation).filter(LabChangeInterpretation.change_id.in_(change_ids)).delete(synchronize_session=False)
        db.query(Change).filter(Change.id.in_(change_ids)).delete(synchronize_session=False)
    if document_ids:
        db.query(Analysis).filter(Analysis.document_id.in_(document_ids)).delete(synchronize_session=False)
        db.query(Document).filter(Document.id.in_(document_ids)).delete(synchronize_session=False)
    db.delete(source)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _to_document_read(document: Document) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        source_id=document.source_id,
        canonical_url=document.canonical_url,
        title=document.title,
        content_text=document.content_text,
        authors=document.authors,
        content_level=document.content_level,
        published_at=document.published_at,
        fetched_at=document.fetched_at,
        status=document.status,
        source_title=document.source.title,
        source_type=document.source.source_type,
        source_url=document.source.url,
    )


@router.get("/api/documents/{document_id}", response_model=DocumentRead)
def document_detail(document_id: str, db: Session = Depends(get_db)) -> DocumentRead:
    document = db.scalar(select(Document).where(Document.id == document_id).options(selectinload(Document.source)))
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return _to_document_read(document)



@router.post("/api/ingest/run", response_model=list[IngestResult])
def run_ingestion(source_id: Optional[str] = None, db: Session = Depends(get_db)) -> list[IngestResult]:
    query = select(Source).order_by(Source.title.asc())
    if source_id:
        query = query.where(Source.id == source_id)
    sources = [source for source in db.scalars(query).all() if source.enabled]
    if source_id and not sources:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    results = []
    for source in sources:
        result = ingest_source(db, source)
        results.append(IngestResult(source_id=source.id, source_title=source.title, **result))
    return results


def _to_analysis_read(analysis) -> AnalysisRead:
    return AnalysisRead(
        id=analysis.id,
        document_id=analysis.document_id,
        relevance_score=float(analysis.relevance_score),
        is_relevant=analysis.is_relevant,
        category=analysis.category,
        matched_entities=analysis.matched_entities,
        extracted_facts=analysis.extracted_facts,
        summary=analysis.summary,
        confidence=float(analysis.confidence) if analysis.confidence is not None else None,
        evidence_citations=analysis.evidence_citations,
        provider=analysis.provider,
        status=analysis.status,
        analyzed_at=analysis.analyzed_at,
        generated_change_id=(analysis.raw_result or {}).get("generated_change_id"),
    )


@router.get("/api/analyses/recent", response_model=list[AnalysisRead])
def recent_analyses(db: Session = Depends(get_db)) -> list[AnalysisRead]:
    from app.db.models import Analysis

    analyses = db.scalars(select(Analysis).order_by(Analysis.analyzed_at.desc()).limit(50)).all()
    return [_to_analysis_read(analysis) for analysis in analyses]


@router.post("/api/analyze/run", response_model=AnalysisRunResult)
def run_analysis(document_id: Optional[str] = None, db: Session = Depends(get_db)) -> AnalysisRunResult:
    from app.services.analyzer import analyze_pending_documents

    analyses, generated_changes = analyze_pending_documents(db, document_id)
    return AnalysisRunResult(
        analyzed=len(analyses),
        relevant=sum(1 for analysis in analyses if analysis.is_relevant),
        generated_changes=generated_changes,
        results=[_to_analysis_read(analysis) for analysis in analyses],
    )


def _to_radar_run_read(run: RadarRun) -> RadarRunRead:
    return RadarRunRead(
        id=run.id,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        source_count=run.source_count,
        documents_fetched=run.documents_fetched,
        documents_created=run.documents_created,
        analyzed=run.analyzed,
        relevant=run.relevant,
        generated_changes=run.generated_changes,
        analysis_total=run.analysis_total or 0,
        dify_requests_total=run.dify_requests_total or 0,
        dify_requests_succeeded=run.dify_requests_succeeded or 0,
        dify_requests_failed=run.dify_requests_failed or 0,
        processed_sources=run.processed_sources or 0,
        total_sources=run.total_sources or run.source_count,
        current_source=run.current_source,
        phase=run.phase or ("completed" if run.finished_at else "starting"),
        errors=run.errors,
    )


@router.get("/api/radar/runs", response_model=list[RadarRunRead])
def recent_radar_runs(db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> list[RadarRunRead]:
    runs = db.scalars(select(RadarRun).order_by(RadarRun.started_at.desc()).limit(20)).all()
    return [_to_radar_run_read(run) for run in runs]


def _run_radar_background(run_id: str) -> None:
    with SessionLocal() as db:
        run = db.get(RadarRun, run_id)
        if run is not None:
            run_radar(db, run)


@router.post("/api/radar/run", response_model=RadarRunRead)
def radar_run(background_tasks: BackgroundTasks, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> RadarRunRead:
    active_run = db.scalar(select(RadarRun).where(RadarRun.status == "running").order_by(RadarRun.started_at.desc()).limit(1))
    if active_run is not None:
        raise HTTPException(status_code=409, detail="雷达正在运行中，请等待当前运行完成。")
    run = RadarRun(id=f"run-{hashlib.sha256(utc_now().isoformat().encode('utf-8')).hexdigest()[:24]}", started_at=utc_now(), status="running", errors=[], phase="starting")
    db.add(run)
    db.commit()
    db.refresh(run)
    background_tasks.add_task(_run_radar_background, run.id)
    return _to_radar_run_read(run)


def _to_schedule_read(config: RadarSettings) -> ScheduleRead:
    return ScheduleRead(enabled=config.enabled, run_time=config.run_time, timezone=config.timezone, last_run_date=config.last_run_date, updated_at=config.updated_at)


@router.get("/api/admin/schedule", response_model=ScheduleRead)
def get_schedule(db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> ScheduleRead:
    config = db.get(RadarSettings, "default")
    if config is None:
        config = RadarSettings(id="default", enabled=False, run_time="08:00", timezone="Asia/Tokyo")
        db.add(config)
        db.commit()
        db.refresh(config)
    return _to_schedule_read(config)


@router.put("/api/admin/schedule", response_model=ScheduleRead)
def update_schedule(payload: ScheduleUpdate, db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> ScheduleRead:
    try:
        datetime.strptime(payload.run_time, "%H:%M")
        ZoneInfo(payload.timezone)
    except Exception as error:
        raise HTTPException(status_code=422, detail="Invalid run_time or timezone") from error
    config = db.get(RadarSettings, "default")
    if config is None:
        config = RadarSettings(id="default")
        db.add(config)
    config.enabled = payload.enabled
    config.run_time = payload.run_time
    config.timezone = payload.timezone
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_schedule_read(config)


@router.get("/api/labs/{lab_id}/changes/today", response_model=list[LabChangeCard])
def lab_today_changes(lab_id: str, request: Request, db: Session = Depends(get_db)) -> list[LabChangeCard]:
    require_lab_access(request, lab_id, db)
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")

    today = _today_start()
    valid_changes = {change.id for change in _changes_by_published_window(db, today, today + timedelta(days=1))}
    interpretations = db.scalars(select(LabChangeInterpretation).where(LabChangeInterpretation.lab_id == lab_id, LabChangeInterpretation.change_id.in_(valid_changes)).options(selectinload(LabChangeInterpretation.lab), selectinload(LabChangeInterpretation.change).selectinload(Change.interpretations).selectinload(LabChangeInterpretation.lab)).order_by(LabChangeInterpretation.relevance_score.desc())).all()
    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return [_to_lab_change_card(interpretation, watch_item_names, _change_published_at(db, interpretation.change)) for interpretation in interpretations]


@router.get("/api/labs/{lab_id}/changes/week", response_model=list[LabChangeCard])
def lab_week_changes(lab_id: str, request: Request, db: Session = Depends(get_db)) -> list[LabChangeCard]:
    require_lab_access(request, lab_id, db)
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")
    today = _today_start()
    week_start = today - timedelta(days=today.weekday())
    valid_changes = {change.id for change in _changes_by_published_window(db, week_start, today)}
    interpretations = db.scalars(select(LabChangeInterpretation).where(LabChangeInterpretation.lab_id == lab_id, LabChangeInterpretation.change_id.in_(valid_changes)).options(selectinload(LabChangeInterpretation.lab), selectinload(LabChangeInterpretation.change).selectinload(Change.interpretations).selectinload(LabChangeInterpretation.lab)).order_by(LabChangeInterpretation.relevance_score.desc())).all()
    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return [_to_lab_change_card(interpretation, watch_item_names, _change_published_at(db, interpretation.change)) for interpretation in interpretations]


@router.get("/api/labs/{lab_id}/changes/month", response_model=list[LabChangeCard])
def lab_month_changes(lab_id: str, request: Request, db: Session = Depends(get_db)) -> list[LabChangeCard]:
    require_lab_access(request, lab_id, db)
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")
    today = _today_start()
    month_start = today.replace(day=1)
    valid_changes = {change.id for change in _changes_by_published_window(db, month_start, today)}
    interpretations = db.scalars(select(LabChangeInterpretation).where(LabChangeInterpretation.lab_id == lab_id, LabChangeInterpretation.change_id.in_(valid_changes)).options(selectinload(LabChangeInterpretation.lab), selectinload(LabChangeInterpretation.change).selectinload(Change.interpretations).selectinload(LabChangeInterpretation.lab)).order_by(LabChangeInterpretation.relevance_score.desc())).all()
    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return [_to_lab_change_card(interpretation, watch_item_names, _change_published_at(db, interpretation.change)) for interpretation in interpretations]


@router.get("/api/changes/{change_id}", response_model=ChangeDetail)
def change_detail(change_id: str, db: Session = Depends(get_db)) -> ChangeDetail:
    change = db.scalar(
        select(Change)
        .where(Change.id == change_id)
        .options(selectinload(Change.interpretations).selectinload(LabChangeInterpretation.lab))
    )
    if change is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change not found")

    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return ChangeDetail(**_to_change_card(change, watch_item_names, _change_published_at(db, change)).model_dump(), status=change.status)


@router.get("/api/translations/{change_id}")
def translate_change(change_id: str, locale: str, lab_id: Optional[str] = None, db: Session = Depends(get_db)) -> dict[str, object]:
    """Translate one article on demand; the stored source remains unchanged."""
    if locale not in {"en", "zh", "ja"}:
        raise HTTPException(status_code=422, detail="locale must be en, zh or ja")
    change = db.scalar(select(Change).where(Change.id == change_id))
    if change is None:
        raise HTTPException(status_code=404, detail="Change not found")
    evidence = change.evidence[0] if change.evidence else {}
    document = db.get(Document, evidence.get("document_id")) if isinstance(evidence, dict) else None
    source_text = document.content_text if document else (evidence.get("evidence_text", "") if isinstance(evidence, dict) else "")
    source_title = document.title if document else change.title
    interpretation = next((item for item in change.interpretations if not lab_id or item.lab_id == lab_id), None)
    why_relevant = interpretation.why_relevant if interpretation else ""
    impact = interpretation.impact if interpretation else ""
    labels = {"en": "English", "zh": "Simplified Chinese", "ja": "Japanese"}
    source_has_cjk = bool(re.search(r"[\u3400-\u9fff]", f"{source_title} {source_text} {change.change_summary} {why_relevant} {impact}"))
    if locale == "zh" or (locale == "en" and not source_has_cjk):
        return {"locale": locale, "provider": "source", "title": source_title, "content": source_text, "summary": change.change_summary, "facts": change.new_facts, "why_relevant": why_relevant, "impact": impact}
    schema = {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "summary": {"type": "string"}, "facts": {"type": "array", "items": {"type": "string"}}, "why_relevant": {"type": "string"}, "impact": {"type": "string"}}, "required": ["title", "content", "summary", "facts", "why_relevant", "impact"], "additionalProperties": False}
    prompt = f"Translate the following research article and Lab interpretation into {labels[locale]}. Preserve technical terms and do not add facts. Return the title, the complete supplied content, a concise translated summary, translated facts, and translations of why_relevant and impact.\nTitle: {source_title}\nContent: {source_text[:18000]}\nSummary: {change.change_summary}\nFacts: {change.new_facts}\nWhy relevant: {why_relevant}\nImpact: {impact}"
    try:
        translated = call_ai_json(prompt, f"article_translation_{locale}", schema)
        return {"locale": locale, "provider": active_provider(), **translated}
    except (AIUnavailableError, KeyError, TypeError, ValueError):
        return {"locale": "en", "provider": "source", "title": source_title, "content": source_text, "summary": change.change_summary, "facts": change.new_facts, "why_relevant": why_relevant, "impact": impact}
