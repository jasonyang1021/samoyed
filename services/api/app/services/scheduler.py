from __future__ import annotations

import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db.database import SessionLocal
from app.db.models import RadarSettings
from app.services.radar import run_radar


_stop_event = threading.Event()
_thread: threading.Thread | None = None


def _scheduler_loop() -> None:
    while not _stop_event.wait(30):
        db = SessionLocal()
        try:
            config = db.get(RadarSettings, "default")
            if config is None or not config.enabled:
                continue
            try:
                now = datetime.now(ZoneInfo(config.timezone))
            except Exception:
                now = datetime.now().astimezone()
            today = now.date().isoformat()
            if now.strftime("%H:%M") < config.run_time or config.last_run_date == today:
                continue
            result = run_radar(db)
            if result.status != "failed":
                config = db.get(RadarSettings, "default")
                if config:
                    config.last_run_date = today
                    db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def start_scheduler() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_scheduler_loop, name="research-radar-scheduler", daemon=True)
    _thread.start()


def stop_scheduler() -> None:
    _stop_event.set()
