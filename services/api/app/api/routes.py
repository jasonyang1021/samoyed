from __future__ import annotations

from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import urlopen

import redis
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import case, create_engine, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Change, Lab, LabChangeInterpretation, WatchItem
from app.schemas.change import ChangeCard, ChangeDetail, LabChangeCard
from app.schemas.lab import LabRead
from app.schemas.watch import WatchItemCreate, WatchItemRead

router = APIRouter()


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


def _affected_labs(change: Change) -> list[str]:
    return [interpretation.lab.name for interpretation in change.interpretations if interpretation.lab]


def _to_change_card(change: Change, watch_item_names: dict[str, str] | None = None) -> ChangeCard:
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
    )


def _to_lab_change_card(interpretation: LabChangeInterpretation, watch_item_names: dict[str, str] | None = None) -> LabChangeCard:
    change = interpretation.change
    return LabChangeCard(
        **_to_change_card(change, watch_item_names).model_dump(),
        why_relevant=interpretation.why_relevant,
        impact=interpretation.impact,
        lab_next_watch_points=interpretation.next_watch_points,
    )


def _today_start() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


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
    changes = db.scalars(
        select(Change)
        .where(Change.detected_at >= _today_start())
        .options(selectinload(Change.interpretations).selectinload(LabChangeInterpretation.lab))
        .order_by(_importance_order(), Change.detected_at.desc())
    ).all()
    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return [_to_change_card(change, watch_item_names) for change in changes]


@router.get("/api/labs", response_model=list[LabRead])
def labs(db: Session = Depends(get_db)) -> list[LabRead]:
    return [
        LabRead(id=lab.id, name=lab.name, description=lab.description)
        for lab in db.scalars(select(Lab).order_by(Lab.name.asc())).all()
    ]


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


@router.get("/api/labs/{lab_id}/changes/today", response_model=list[LabChangeCard])
def lab_today_changes(lab_id: str, db: Session = Depends(get_db)) -> list[LabChangeCard]:
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found")

    interpretations = db.scalars(
        select(LabChangeInterpretation)
        .where(LabChangeInterpretation.lab_id == lab_id)
        .join(LabChangeInterpretation.change)
        .where(Change.detected_at >= _today_start())
        .options(
            selectinload(LabChangeInterpretation.lab),
            selectinload(LabChangeInterpretation.change)
            .selectinload(Change.interpretations)
            .selectinload(LabChangeInterpretation.lab),
        )
        .order_by(_importance_order(), LabChangeInterpretation.relevance_score.desc())
    ).all()
    watch_item_names = {item.id: item.name for item in db.scalars(select(WatchItem)).all()}
    return [_to_lab_change_card(interpretation, watch_item_names) for interpretation in interpretations]


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
    return ChangeDetail(**_to_change_card(change, watch_item_names).model_dump(), status=change.status)
