from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from urllib.error import URLError
from urllib.request import urlopen

import redis
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import case, create_engine, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Change, Document, Lab, LabChangeInterpretation, LabInvitation, LabMembership, LabProfile, LabWatchItem, RadarRun, RadarSettings, Source, User, WatchItem
from app.schemas.analysis import AnalysisRead, AnalysisRunResult
from app.schemas.document import DocumentRead, IngestResult, SourceRead
from app.schemas.change import ChangeCard, ChangeDetail, LabChangeCard
from app.schemas.lab import LabCreate, LabRead, LabUpdate, LabWatchItemCreate, LabWatchItemRead
from app.schemas.radar import RadarRunRead
from app.schemas.watch import WatchItemCreate, WatchItemRead
from app.schemas.schedule import ScheduleRead, ScheduleUpdate
from app.schemas.auth import AuthUserRead, LabInvitationCreate, LabInvitationRead, LabMembershipRead, LabMembershipUpdate
from app.services.ingestion import ingest_source
from app.services.analyzer import analyze_pending_documents
from app.services.radar import run_radar
from app.services.ai_gateway import AIUnavailableError, active_provider, call_ai_json, check_dify_connection
from app.services.auth import create_session, exchange_google_code, google_authorization_url, google_enabled, google_state, read_session, session_profile, sync_user

router = APIRouter()


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


@router.get("/health")
def health() -> dict[str, str]:
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
    return {"configured": provider != "rule_based", "provider": provider, "model": settings.openai_model, "web_search_enabled": settings.openai_ai_search_enabled}


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
    changes = _changes_by_published_window(db, week_start, today)
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
        LabRead(id=lab.id, name=lab.name, description=lab.description)
        for lab in db.scalars(select(Lab).order_by(Lab.name.asc())).all()
    ]


@router.get("/api/labs/{lab_id}", response_model=LabRead)
def lab_detail(lab_id: str, db: Session = Depends(get_db)) -> LabRead:
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    return LabRead(id=lab.id, name=lab.name, description=lab.description)


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
    db.commit()
    db.refresh(lab)
    return LabRead(id=lab.id, name=lab.name, description=lab.description)


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
    db.commit()
    db.refresh(lab)
    return LabRead(id=lab.id, name=lab.name, description=lab.description)


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
    if db.get(Lab, lab_id) is None:
        raise HTTPException(status_code=404, detail="Lab not found")
    links = db.query(LabWatchItem).filter(LabWatchItem.lab_id == lab_id).all()
    if links:
        return [_lab_watch_item_read(link.watch_item) for link in links]
    return []


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
        docs = list(source.documents)
        published = [document.published_at for document in docs if document.published_at]
        fetched = [document.fetched_at for document in docs if document.fetched_at]
        result.append(SourceRead(id=source.id, source_type=source.source_type, title=source.title, url=source.url, format=(source.raw_metadata or {}).get("format"), document_count=len(docs), latest_published_at=max(published) if published else None, latest_fetched_at=max(fetched) if fetched else None, status="有数据" if docs else ("可抓取" if source.url and (source.raw_metadata or {}).get("format") else "未配置")))
    return result


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
    sources = db.scalars(query).all()
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
        errors=run.errors,
    )


@router.get("/api/radar/runs", response_model=list[RadarRunRead])
def recent_radar_runs(db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> list[RadarRunRead]:
    runs = db.scalars(select(RadarRun).order_by(RadarRun.started_at.desc()).limit(20)).all()
    return [_to_radar_run_read(run) for run in runs]


@router.post("/api/radar/run", response_model=RadarRunRead)
def radar_run(db: Session = Depends(get_db), _: Optional[dict] = Depends(require_admin)) -> RadarRunRead:
    return _to_radar_run_read(run_radar(db))


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
def lab_today_changes(lab_id: str, db: Session = Depends(get_db)) -> list[LabChangeCard]:
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")

    today = _today_start()
    valid_changes = {change.id for change in _changes_by_published_window(db, today, today + timedelta(days=1))}
    interpretations = db.scalars(select(LabChangeInterpretation).where(LabChangeInterpretation.lab_id == lab_id, LabChangeInterpretation.change_id.in_(valid_changes)).options(selectinload(LabChangeInterpretation.lab), selectinload(LabChangeInterpretation.change).selectinload(Change.interpretations).selectinload(LabChangeInterpretation.lab)).order_by(LabChangeInterpretation.relevance_score.desc())).all()
    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return [_to_lab_change_card(interpretation, watch_item_names, _change_published_at(db, interpretation.change)) for interpretation in interpretations]


@router.get("/api/labs/{lab_id}/changes/week", response_model=list[LabChangeCard])
def lab_week_changes(lab_id: str, db: Session = Depends(get_db)) -> list[LabChangeCard]:
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
def lab_month_changes(lab_id: str, db: Session = Depends(get_db)) -> list[LabChangeCard]:
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
def translate_change(change_id: str, locale: str, db: Session = Depends(get_db)) -> dict[str, object]:
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
    labels = {"en": "English", "zh": "Simplified Chinese", "ja": "Japanese"}
    if locale == "en":
        return {"locale": locale, "provider": "source", "title": source_title, "content": source_text, "summary": change.change_summary, "facts": change.new_facts}
    schema = {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "summary": {"type": "string"}, "facts": {"type": "array", "items": {"type": "string"}}}, "required": ["title", "content", "summary", "facts"], "additionalProperties": False}
    prompt = f"Translate the following research article into {labels[locale]}. Preserve technical terms and do not add facts. Return the title, the complete supplied content, a concise translated summary, and translated facts.\nTitle: {source_title}\nContent: {source_text[:18000]}\nSummary: {change.change_summary}\nFacts: {change.new_facts}"
    try:
        translated = call_ai_json(prompt, f"article_translation_{locale}", schema)
        return {"locale": locale, "provider": active_provider(), **translated}
    except (AIUnavailableError, KeyError, TypeError, ValueError):
        return {"locale": "en", "provider": "source", "title": source_title, "content": source_text, "summary": change.change_summary, "facts": change.new_facts}
