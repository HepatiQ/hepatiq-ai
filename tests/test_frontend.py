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

    band_html = [m.value for m in at.markdown if "Risk band" in m.value]
    assert len(band_html) == 1
    assert any(tag in band_html[0] for tag in ("Low", "Intermediate", "High"))
    assert any("Scored in" in c.value for c in at.caption)

    assert "Recent predictions (local history)" in [e.label for e in at.expander]
    assert len(at.dataframe) >= 1  # the prediction we just made is in the history table


def test_clear_history_wipes_table():
    """Clear history button DELETEs server-side rows and refreshes the panel."""
    if not _backend_reachable():
        if os.environ.get("CI"):
            pytest.fail("backend on localhost:8000 unreachable in CI — uvicorn start step broken")
        pytest.skip("backend on localhost:8000 not running")

    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    assert not at.exception, at.exception

    at.button[0].click().run()  # "Compute risk" -> a row lands in history
    assert not at.exception, at.exception
    assert len(at.dataframe) == 1

    at.button[1].click().run()  # "Clear history"
    assert not at.exception, at.exception
    assert len(at.dataframe) == 0
    assert any("No predictions logged yet." in c.value for c in at.caption)


class _StubPredictResponse:
    status_code = 200

    def __init__(self):
        self._body = {
            "probability": 0.5,
            "risk_band": "high",
            "contributions": [],
            "model_loaded": True,
            "model_version": "deadbeef",
            "warnings": ["age=120 is outside the training range [29, 77] — the model is extrapolating"],
        }

    def json(self):
        return self._body

    def raise_for_status(self):
        return None


def _stub_predict_post(monkeypatch) -> dict:
    """Replace requests.post with a stub; returns a shared call counter."""
    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        return _StubPredictResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    return calls


def test_widget_edit_does_not_post(monkeypatch):
    """Editing form widgets (or any rerun without submit) must never POST."""
    calls = _stub_predict_post(monkeypatch)
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    assert not at.exception, at.exception

    at.number_input[0].set_value(61.0)  # Age
    at.run()
    assert not at.exception, at.exception
    assert calls["count"] == 0
    assert len(at.metric) == 0  # nothing rendered without a submit


def test_result_persists_across_reruns(monkeypatch):
    """Scorecard renders from session state, surviving unrelated reruns."""
    calls = _stub_predict_post(monkeypatch)
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    assert len(at.metric) == 1
    assert at.metric[0].value == "50.0%"

    at.run()  # unrelated rerun must neither lose the result nor re-POST
    assert not at.exception, at.exception
    assert len(at.metric) == 1
    assert calls["count"] == 1


def test_rapid_double_submit_posts_once(monkeypatch):
    """Two identical submits inside the dedupe window produce one POST."""
    calls = _stub_predict_post(monkeypatch)
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    at.button[0].click().run()
    assert not at.exception, at.exception

    assert calls["count"] == 1
    assert len(at.metric) == 1


def test_number_input_steps_match_display_precision():
    """Steppers must advance visibly at each widget's format precision.

    Regression: default float step 0.01 made Age's +/- look dead (55.0 ->
    55.01 rendered as '55.0' at %.1f) and left other fields glacial.
    The explicit per-field step values below are the guard: if a step
    regresses to the 0.01 default, this test fails.
    """
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    assert not at.exception, at.exception

    steps = [w.proto.step for w in at.number_input]
    assert steps == [1.0, 0.1, 0.1, 1.0, 1.0, 1.0, 0.1, 1.0, 1.0, 0.1]


def test_band_warning_and_latency_render(monkeypatch):
    """Scorecard shows risk band, extrapolation warning, latency + version."""
    _stub_predict_post(monkeypatch)
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    at.button[0].click().run()
    assert not at.exception, at.exception

    band_html = [m.value for m in at.markdown if "Risk band" in m.value]
    assert len(band_html) == 1
    assert "High" in band_html[0]

    assert len(at.warning) == 1
    assert "outside the training range" in at.warning[0].value

    captions = [c.value for c in at.caption]
    assert any("Scored in" in msg and "model deadbeef" in msg for msg in captions)
    assert any("not a medical device" in msg for msg in captions)


def test_history_limit_selectbox_defaults_to_10():
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    limit_selects = [s for s in at.selectbox if s.label == "Show"]
    assert len(limit_selects) == 1
    assert limit_selects[0].value == 10
