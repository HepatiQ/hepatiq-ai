"""GET /history: every prediction is logged and retrievable with its inputs."""

from tests.conftest import REQUIRED_ONLY, SAMPLE_FULL


def test_prediction_is_logged(client):
    prob = client.post("/predict", json=REQUIRED_ONLY).json()["probability"]
    items = client.get("/history").json()["items"]
    assert len(items) == 1
    assert abs(items[0]["probability"] - prob) < 1e-12
    assert items[0]["request"]["sex"] == "f"
    assert items[0]["request"]["age"] == 58.0
    assert len(items[0]["contributions"]) == 17
    assert isinstance(items[0]["id"], int)
    assert items[0]["created_at"]


def test_history_is_newest_first(client):
    client.post("/predict", json=REQUIRED_ONLY)
    client.post("/predict", json=SAMPLE_FULL)
    items = client.get("/history").json()["items"]
    assert len(items) == 2
    assert items[0]["id"] > items[1]["id"]
    assert items[0]["request"]["trt"] == 1.0
    assert items[1]["request"].get("trt") is None


def test_history_respects_limit(client):
    for _ in range(3):
        client.post("/predict", json=REQUIRED_ONLY)
    assert len(client.get("/history?limit=2").json()["items"]) == 2
    assert len(client.get("/history?limit=1").json()["items"]) == 1


def test_history_limit_is_validated(client):
    assert client.get("/history?limit=0").status_code == 422
    assert client.get("/history?limit=101").status_code == 422


def test_delete_history_clears_all_rows(client):
    client.post("/predict", json=REQUIRED_ONLY)
    client.post("/predict", json=SAMPLE_FULL)
    r = client.delete("/history")
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] == 2
    assert client.get("/history").json()["items"] == []


def test_delete_history_on_empty_db_is_ok(client):
    r = client.delete("/history")
    assert r.status_code == 200
    assert r.json()["deleted"] == 0
