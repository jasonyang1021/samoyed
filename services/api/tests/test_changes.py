from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_today_changes_returns_seeded_change_cards() -> None:
    response = client.get("/api/changes/today")

    assert response.status_code == 200
    changes = response.json()
    assert len(changes) == 3
    assert changes[0]["id"] == "chg-001"
    assert changes[0]["importance"] in {"S", "A", "B", "C"}
    assert changes[0]["new_facts"]
    assert changes[0]["previous_state"]
    assert changes[0]["current_state"]
    assert changes[0]["evidence"]
    assert changes[0]["next_watch_points"]
    assert "Glass Core Lab" in changes[0]["affected_labs"]


def test_labs_returns_glass_core_lab() -> None:
    response = client.get("/api/labs")

    assert response.status_code == 200
    labs = response.json()
    assert labs == [
        {
            "id": "lab-glass-core",
            "name": "Glass Core Lab",
            "description": "关注玻璃基板、TGV、先进封装载板与量产可靠性的 Lab。",
        }
    ]


def test_lab_today_changes_returns_lab_interpretations() -> None:
    response = client.get("/api/labs/lab-glass-core/changes/today")

    assert response.status_code == 200
    changes = response.json()
    assert len(changes) == 3
    assert changes[0]["why_relevant"]
    assert changes[0]["impact"]
    assert changes[0]["lab_next_watch_points"]


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
