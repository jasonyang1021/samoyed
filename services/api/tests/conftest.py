import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import Change, EntityState, Lab, LabChangeInterpretation, LabProfile, Source, WatchItem
from examples.demo_seed import seed_database
from app.main import app
from app.api.routes import require_admin


@pytest.fixture(autouse=True)
def test_database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as db:
        seed_database(db)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_admin] = lambda: None
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
