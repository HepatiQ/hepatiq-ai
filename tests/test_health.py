"""GET /health contract: model + explainer load state and 17-feature surface."""


def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_health_reports_model_loaded(client):
    h = client.get("/health").json()
    assert h["model_loaded"] is True
    assert h["status"] == "ok"


def test_health_reports_17_features(client):
    h = client.get("/health").json()
    assert h["n_features"] == 17


def test_health_explainer_ready_no_error(client):
    h = client.get("/health").json()
    assert h["explainer_ready"] is True
    assert h["error"] is None
    assert h["model_path"].endswith("model.pkl")


def test_health_reports_model_version(client):
    h = client.get("/health").json()
    assert isinstance(h["model_version"], str)
    assert len(h["model_version"]) == 8
