from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_today_changes_excludes_changes_without_published_documents() -> None:
    response = client.get("/api/changes/today")

    assert response.status_code == 200
    changes = response.json()
    assert changes == []


def test_labs_returns_seeded_labs() -> None:
    response = client.get("/api/labs")

    assert response.status_code == 200
    labs = response.json()
    assert [lab["name"] for lab in labs] == ["CC Lab", "CPO Lab", "Fujii Lab", "Glass Core Lab", "PCB Lab"]
    assert all(lab["description"] for lab in labs)


def test_lab_today_changes_excludes_undated_seed_interpretations() -> None:
    response = client.get("/api/labs/lab-glass-core/changes/today")

    assert response.status_code == 200
    changes = response.json()
    assert changes == []


def test_change_detail_returns_evidence_and_watch_points() -> None:
    response = client.get("/api/changes/chg-001")

    assert response.status_code == 200
    change = response.json()
    assert change["id"] == "chg-001"
    assert change["status"] == "detected"
    assert change["evidence"][0]["source_id"] == "src-glass-core-engineering"


def test_missing_change_returns_404() -> None:
    response = client.get("/api/changes/not-found")

    assert response.status_code == 404


def test_missing_lab_returns_404() -> None:
    response = client.get("/api/labs/not-found/changes/today")

    assert response.status_code == 404


def test_watch_items_returns_followed_topics_and_companies() -> None:
    response = client.get("/api/watch-items")

    assert response.status_code == 200
    items = response.json()
    assert {item["name"] for item in items} >= {"Glass Core", "Intel", "ECTC"}
    assert all(item["is_following"] for item in items)


def test_watch_items_can_be_created() -> None:
    response = client.post(
        "/api/watch-items",
        json={"kind": "professor", "name": "张教授", "description": "Glass Core 可靠性研究"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "张教授"
    assert response.json()["kind"] == "professor"
