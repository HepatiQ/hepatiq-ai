"""Failure paths: unavailable model and unavailable history database must yield 503s, never 500s."""

from fastapi.testclient import TestClient

from hepatiq.backend import main as main_module
from tests.conftest import REQUIRED_ONLY


def test_predict_returns_503_when_model_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "MODEL_PATH", tmp_path / "missing.pkl")
    with TestClient(main_module.app) as c:
        h = c.get("/health")
        assert h.status_code == 200
        assert h.json()["model_loaded"] is False
        assert h.json()["error"] == "model unavailable"
        assert "missing.pkl" not in h.text
        r = c.post("/predict", json=REQUIRED_ONLY)
        assert r.status_code == 503
        assert r.json()["detail"] == "Model not loaded"
        assert "missing.pkl" not in r.text


def test_history_returns_503_and_recovers_when_db_unavailable(client):
    saved = main_module._state["db_path"]
    try:
        main_module._state["db_path"] = None
        r = client.get("/history")
        assert r.status_code == 503
        assert "unavailable" in r.json()["detail"].lower()
    finally:
        main_module._state["db_path"] = saved
    assert client.get("/history").status_code == 200
