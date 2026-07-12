"""Production-safe database bootstrap.

The application bootstrap intentionally creates infrastructure settings only.
Demo/domain data lives in ``services/api/examples/demo_seed.py`` and must be
loaded explicitly by a developer.
"""

from app.db.database import SessionLocal
from app.db.models import RadarSettings
from app.core.config import settings


def seed_database(db) -> None:
    if db.get(RadarSettings, "default") is None:
        db.add(RadarSettings(id="default", enabled=False, run_time="08:00", timezone="Asia/Tokyo"))
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed_database(db)
        if settings.seed_demo_data:
            from examples.demo_seed import seed_database as seed_demo_database

            seed_demo_database(db)


if __name__ == "__main__":
    main()
