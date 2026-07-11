from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_dependency_status(monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "_check_postgres", lambda: "ok")
    monkeypatch.setattr(routes, "_check_redis", lambda: "ok")
    monkeypatch.setattr(routes, "_check_minio", lambda: "ok")

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"] == {
        "api": "ok",
        "postgres": "ok",
        "redis": "ok",
        "minio": "ok",
    }


def test_readiness_returns_503_when_dependency_is_unavailable(monkeypatch) -> None:
    from app.api import routes

    monkeypatch.setattr(routes, "_check_postgres", lambda: "ok")
    monkeypatch.setattr(routes, "_check_redis", lambda: "ok")

    def unavailable_minio() -> str:
        raise TimeoutError("MinIO is not reachable")

    monkeypatch.setattr(routes, "_check_minio", unavailable_minio)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["minio"] == "unavailable"
