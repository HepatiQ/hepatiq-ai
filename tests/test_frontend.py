"""Streamlit AppTest smoke: the frontend script executes without exceptions."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

FRONTEND = Path(__file__).resolve().parents[1] / "frontend" / "app.py"


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
