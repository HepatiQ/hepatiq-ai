"""Streamlit AppTest smoke: the frontend script executes without exceptions."""

import os
import sys
from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend" / "app.py"

sys.path.insert(0, str(REPO_ROOT))

from tests.conftest import build_model_frame  # noqa: E402


def test_frontend_renders_without_exception():
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    assert not at.exception, at.exception


def test_frontend_form_has_required_inputs():
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    labels = [w.label for w in at.number_input] + [w.label for w in at.selectbox]
    assert any("Age" in label for label in labels)
    assert any("Bilirubin" in label for label in labels)
    assert any("Sex" == label for label in labels)


def _backend_reachable() -> bool:
    try:
        return requests.get("http://localhost:8000/health", timeout=3).status_code == 200
    except requests.exceptions.RequestException:
        return False


def test_form_submit_renders_scorecard():
    """True E2E: form -> real HTTP -> FastAPI -> model -> rendered scorecard."""
    if not _backend_reachable():
        if os.environ.get("CI"):
            pytest.fail("backend on localhost:8000 unreachable in CI — uvicorn start step broken")
        pytest.skip("backend on localhost:8000 not running")

    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    assert not at.exception, at.exception

    at.number_input[0].set_value(61.0)  # Age
    at.number_input[1].set_value(3.4)   # Bilirubin
    at.button[0].click().run()          # "Compute risk"
    assert not at.exception, at.exception

    assert len(at.metric) == 1
    assert at.metric[0].label == "Estimated 5-year severe event risk"
    assert at.metric[0].value.endswith("%")

    direct = build_model_frame(
        {"age": 61.0, "sex": "f", "edema": 0.0, "bili": 3.4, "albumin": 3.5}
    )
    import joblib

    from backend.main import MODEL_PATH

    expected = float(joblib.load(MODEL_PATH).predict_proba(direct)[0, 1])
    assert at.metric[0].value == f"{expected:.1%}"

    assert len(at.get("plotly_chart")) == 1  # SHAP contributions chart

    assert [e.label for e in at.expander] == ["Recent predictions (local history)"]
    assert len(at.dataframe) == 1  # the prediction we just made is in the history table
