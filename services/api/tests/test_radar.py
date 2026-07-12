from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import routes
from app.db.models import RadarRun
from app.main import app


client = TestClient(app)


def test_radar_runs_starts_empty() -> None:
    response = client.get("/api/radar/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_schedule_settings_can_be_updated() -> None:
    response = client.get("/api/admin/schedule")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    updated = client.put("/api/admin/schedule", json={"enabled": True, "run_time": "09:30", "timezone": "Asia/Tokyo"})

    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
    assert updated.json()["run_time"] == "09:30"


def test_ai_status_reports_configuration_without_exposing_key(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "ai_provider", "rule_based")
    monkeypatch.setattr(settings, "dify_api_key", None)
    response = client.get("/api/ai/status")

    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert "api_key" not in response.json()


def test_radar_run_endpoint_returns_pipeline_summary(monkeypatch) -> None:
    monkeypatch.setattr(routes, "_run_radar_background", lambda run_id: None)

    response = client.post("/api/radar/run")

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["phase"] == "starting"


def test_dify_provider_returns_structured_workflow_output(monkeypatch) -> None:
    import json

    from app.core.config import settings
    from app.services.ai_gateway import call_ai_json

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"data": {"outputs": {"result": '{"is_relevant": true}'}}}).encode()

    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        if request.data:
            captured["body"] = json.loads(request.data.decode())
        return FakeResponse()

    monkeypatch.setattr(settings, "ai_provider", "dify")
    monkeypatch.setattr(settings, "dify_api_key", "dify-test-key")
    monkeypatch.setattr(settings, "dify_base_url", "https://dify.test/v1")
    monkeypatch.setattr("app.services.ai_gateway.urlopen", fake_urlopen)

    result = call_ai_json("判断这条资料", "test_schema", {"type": "object"})

    assert result == {"is_relevant": True}
    assert captured["url"] == "https://dify.test/v1/workflows/run"
    assert captured["timeout"] == settings.dify_request_timeout_seconds
    assert captured["body"]["user"] == "research-radar"
    assert captured["body"]["inputs"]["schema_name"] == "test_schema"


def test_dify_check_does_not_require_a_key(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "dify_api_key", None)
    response = client.get("/api/ai/dify/check")

    assert response.status_code == 200
    assert response.json()["configured"] is False
