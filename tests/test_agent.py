"""ClinicalAgent robustness: missing SHAP impacts must not break the endpoint."""

from hepatiq.backend import main as main_module
from hepatiq.backend.agent import ClinicalAgent
from tests.conftest import REQUIRED_ONLY


def test_agent_skips_none_and_missing_impacts():
    result = ClinicalAgent().reason_loop(
        {},
        0.3,
        [
            {"feature": "age", "value": 58.0, "impact": None},
            {"feature": "bili", "value": 1.2},
            {"feature": "albumin", "value": 3.6, "impact": -0.2},
            {"feature": "edema", "value": 0.0, "impact": 0.5},
        ],
    )
    assert [d["feature"] for d in result["key_drivers"]] == ["edema", "albumin"]
    assert result["assessment"]["band"] == "intermediate"
    assert result["reasoning_steps"] == ["assessed", "identified_drivers"]


def test_agent_reason_endpoint_survives_missing_explainer(client):
    saved = main_module._state["explainer"]
    try:
        main_module._state["explainer"] = None
        r = client.post("/agent/reason", json=REQUIRED_ONLY)
    finally:
        main_module._state["explainer"] = saved
    assert r.status_code == 200, r.text
    assert r.json()["agent_analysis"]["key_drivers"] == []
