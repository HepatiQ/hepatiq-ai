"""Streamlit AppTest smoke: the frontend script executes without exceptions."""

import os
from pathlib import Path

import pytest
import requests
import streamlit as st
from fpdf import FPDF
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from streamlit.testing.v1 import AppTest

from tests.conftest import FEATURE_COLUMNS, build_model_frame

# AppTest executes frontend/app.py, which probes the backend in the sidebar.
# Point it at a reserved-domain host so the probe fails instantly instead of
# waiting on the deployed Render cold start (which can exceed the submit
# dedupe window and make timing-sensitive tests flaky).
os.environ["HEPATIQ_BACKEND_URL"] = "http://hepatiq-backend.invalid:8000"

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "src" / "hepatiq" / "frontend" / "app.py"
E2E_BACKEND_URL = os.environ.get("HEPATIQ_E2E_BACKEND_URL", "http://localhost:8000")


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


def test_sidebar_has_bulk_upload_page_link(monkeypatch):
    calls = []
    real_page_link = st.page_link

    def tracking_page_link(*args, **kwargs):
        calls.append((args, kwargs))
        return real_page_link(*args, **kwargs)

    monkeypatch.setattr(st, "page_link", tracking_page_link)
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    assert any("pages/2_Bulk_Predict.py" in str(call[0]) for call in calls)


def _backend_reachable() -> bool:
    try:
        return requests.get(f"{E2E_BACKEND_URL}/health", timeout=3).status_code == 200
    except requests.exceptions.RequestException:
        return False


def test_form_submit_renders_scorecard(monkeypatch):
    """True E2E: form -> real HTTP -> FastAPI -> model -> rendered scorecard."""
    if not _backend_reachable():
        if os.environ.get("CI"):
            pytest.fail(f"backend on {E2E_BACKEND_URL} unreachable in CI - uvicorn start step broken")
        pytest.skip(f"backend on {E2E_BACKEND_URL} not running")

    monkeypatch.setenv("HEPATIQ_BACKEND_URL", E2E_BACKEND_URL)
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    assert not at.exception, at.exception

    at.number_input[0].set_value(61.0)  # Age
    at.number_input[1].set_value(3.4)   # Bilirubin
    at.button[0].click().run()          # "Compute risk"
    assert not at.exception, at.exception

    assert len(at.metric) == 1
    assert at.metric[0].label == "Estimated 5-Year Risk of Death or Liver Transplantation"
    assert at.metric[0].value.endswith("%")

    direct = build_model_frame(
        {"age": 61.0, "sex": "f", "edema": 0.0, "bili": 3.4, "albumin": 3.5}
    )
    from hepatiq.backend.main import MODEL_PATH
    from hepatiq.model_artifact import load_model

    expected = float(load_model(MODEL_PATH).predict_proba(direct)[0, 1])
    assert at.metric[0].value == f"{expected:.1%}"

    assert len(at.get("plotly_chart")) == 1  # SHAP contributions chart

    band_html = [m.value for m in at.markdown if "Risk band" in m.value]
    assert len(band_html) == 1
    assert any(tag in band_html[0] for tag in ("Low", "Intermediate", "High"))
    assert any("Scored in" in c.value for c in at.caption)

    assert "Recent predictions (local history)" in [e.label for e in at.expander]
    assert len(at.dataframe) >= 1  # the prediction we just made is in the history table


def test_clear_history_wipes_table(monkeypatch):
    """Clear history button DELETEs server-side rows and refreshes the panel."""
    if not _backend_reachable():
        if os.environ.get("CI"):
            pytest.fail(f"backend on {E2E_BACKEND_URL} unreachable in CI - uvicorn start step broken")
        pytest.skip(f"backend on {E2E_BACKEND_URL} not running")

    monkeypatch.setenv("HEPATIQ_BACKEND_URL", E2E_BACKEND_URL)
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


class _StubRateLimitResponse(_StubPredictResponse):
    status_code = 429
    headers = {"Retry-After": "37"}

    def json(self):
        return {"detail": "Too many requests; retry later."}


def _stub_predict_post(monkeypatch) -> dict:
    """Replace requests.post with a stub; returns a shared call counter."""
    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        return _StubPredictResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    return calls


REQUIRED_FEATURES = {"age", "sex", "edema", "bili", "albumin"}


def _stub_contributions(*, all_provided: bool = False) -> list[dict]:
    return [
        {
            "feature": feature,
            "value": 1.0,
            "impact": 0.1 if index % 2 == 0 else -0.05,
            "imputed": not all_provided and feature not in REQUIRED_FEATURES,
        }
        for index, feature in enumerate(FEATURE_COLUMNS)
    ]


def _stub_predict_post_with_contributions(monkeypatch, contributions: list[dict]) -> None:
    class Response(_StubPredictResponse):
        def __init__(self):
            super().__init__()
            self._body["contributions"] = contributions
            self._body["imputed_features"] = [
                c["feature"] for c in contributions if c["imputed"]
            ]

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: Response())


def _capture_download(monkeypatch) -> dict:
    captured: dict = {}
    original = st.download_button

    def fake_download_button(*args, **kwargs):
        captured["data"] = kwargs.get("data")
        return original(*args, **kwargs)

    monkeypatch.setattr(st, "download_button", fake_download_button)
    return captured


def _submit_with_stub(monkeypatch):
    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    return at


def test_pdf_flags_imputed_inputs_and_embeds_charts(monkeypatch):
    """PDF summary names imputed inputs and contains the summary charts."""
    contributions = _stub_contributions()
    _stub_predict_post_with_contributions(monkeypatch, contributions)
    captured = _capture_download(monkeypatch)

    at = _submit_with_stub(monkeypatch)

    assert any("12 of 17 inputs" in item.value for item in at.info)
    pdf = captured["data"]
    assert pdf.startswith(b"%PDF")
    assert b"Imputed inputs" in pdf and b"12 of 17" in pdf
    assert b"Cholesterol: imputed by model" in pdf
    assert pdf.count(b"/Subtype /Image") >= 3


def test_pdf_without_imputed_inputs_reports_none(monkeypatch):
    """A complete payload reports zero imputed inputs, without an info banner."""
    _stub_predict_post_with_contributions(monkeypatch, _stub_contributions(all_provided=True))
    captured = _capture_download(monkeypatch)

    at = _submit_with_stub(monkeypatch)

    assert not at.info
    pdf = captured["data"]
    assert b"Imputed inputs" in pdf and b"0 of 17" in pdf
    assert b"None - all inputs were provided" in pdf


def test_pdf_still_exports_when_charts_fail(monkeypatch):
    """Chart rendering must never remove the imputation indicators from the PDF."""
    import matplotlib.pyplot as plt

    _stub_predict_post_with_contributions(monkeypatch, _stub_contributions())
    captured = _capture_download(monkeypatch)

    def broken_savefig(*args, **kwargs):
        raise RuntimeError("chart backend unavailable")

    monkeypatch.setattr(plt, "savefig", broken_savefig)
    _submit_with_stub(monkeypatch)

    pdf = captured["data"]
    assert pdf.startswith(b"%PDF")
    assert b"Imputed inputs" in pdf and b"12 of 17" in pdf
    assert b"Charts unavailable" in pdf


def test_pdf_footnote_wraps_as_block_with_spacing(monkeypatch):
    """The imputation footnote must be a wrapped block with room below the charts."""
    calls = []
    original_cell = FPDF.cell
    original_multi_cell = FPDF.multi_cell
    original_image = FPDF.image
    original_ln = FPDF.ln

    def spy_cell(self, *args, **kwargs):
        calls.append(("cell", args, kwargs))
        return original_cell(self, *args, **kwargs)

    def spy_multi_cell(self, *args, **kwargs):
        calls.append(("multi_cell", args, kwargs))
        return original_multi_cell(self, *args, **kwargs)

    def spy_image(self, *args, **kwargs):
        calls.append(("image", args, kwargs))
        return original_image(self, *args, **kwargs)

    def spy_ln(self, h=None):
        calls.append(("ln", (h,), {}))
        return original_ln(self, h)

    monkeypatch.setattr(FPDF, "cell", spy_cell)
    monkeypatch.setattr(FPDF, "multi_cell", spy_multi_cell)
    monkeypatch.setattr(FPDF, "image", spy_image)
    monkeypatch.setattr(FPDF, "ln", spy_ln)

    _stub_predict_post_with_contributions(monkeypatch, _stub_contributions())
    _submit_with_stub(monkeypatch)

    footnote_cells = [
        call
        for call in calls
        if call[0] == "cell" and "* = missing input" in str(call[1][2] if len(call[1]) > 2 else "")
    ]
    assert not footnote_cells

    footnote_blocks = [
        call
        for call in calls
        if call[0] == "multi_cell"
        and "* = missing input" in str(call[1][2] if len(call[1]) > 2 else "")
    ]
    assert footnote_blocks

    image_calls = [index for index, call in enumerate(calls) if call[0] == "image"]
    assert len(image_calls) >= 2
    following_ln = next(call for call in calls[image_calls[1] + 1 :] if call[0] == "ln")
    assert following_ln[1][0] >= 6


def test_completeness_legend_stays_inside_reserved_space(monkeypatch):
    """The legend must not be anchored below the chart or crowd the footnote."""
    legends = []
    tight_layouts = []
    original_legend = Axes.legend
    original_tight_layout = Figure.tight_layout

    def spy_legend(self, *args, **kwargs):
        legends.append((args, kwargs))
        return original_legend(self, *args, **kwargs)

    def spy_tight_layout(self, *args, **kwargs):
        tight_layouts.append(kwargs)
        return original_tight_layout(self, *args, **kwargs)

    monkeypatch.setattr(Axes, "legend", spy_legend)
    monkeypatch.setattr(Figure, "tight_layout", spy_tight_layout)

    _stub_predict_post_with_contributions(monkeypatch, _stub_contributions())
    _submit_with_stub(monkeypatch)

    assert legends
    args, kwargs = legends[0]
    anchor = kwargs.get("bbox_to_anchor") or (0.5, 0.5)
    assert anchor[1] >= 0
    labels = list(args[1]) if len(args) > 1 else list(kwargs.get("labels", []))
    assert "Imputed" in labels
    assert "Imputed by model" not in labels
    assert any(kwargs.get("rect", (0, 0, 1, 1))[1] >= 0.3 for kwargs in tight_layouts)


def test_rate_limit_error_rendered(monkeypatch):
    """A 429 should show the server's retry window, not a generic failure."""
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: _StubRateLimitResponse())

    at = AppTest.from_file(str(FRONTEND), default_timeout=60)
    at.run()
    at.button[0].click().run()

    assert not at.exception, at.exception
    errors = [error.value for error in at.error]
    assert any("Too many requests" in error and "37 seconds" in error for error in errors)


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
