"""Streamlit AppTest coverage for the bulk CSV upload page."""

import os
from pathlib import Path

import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

os.environ["HEPATIQ_BACKEND_URL"] = "http://hepatiq-backend.invalid:8000"

REPO_ROOT = Path(__file__).resolve().parents[1]
BULK_PAGE = REPO_ROOT / "src" / "hepatiq" / "frontend" / "pages" / "2_Bulk_Predict.py"

VALID_CSV = b"age,sex,edema,bili,albumin\n61,f,0,3.4,3.5\n68,m,0.5,8.0,2.9\n"
UNKNOWN_COLUMN_CSV = b"age,sex,edema,bili,bilirubin,albumin\n61,f,0,3.4,3.5\n"


class StubResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload
        self.headers = {}

    def json(self):
        return self._payload


def _stub_batch_post(monkeypatch):
    captured = {}
    payload = {
        "total": 2,
        "succeeded": 2,
        "failed": 0,
        "results": [
            {
                "row": 0,
                "prediction": {
                    "probability": 0.097,
                    "risk_band": "low",
                    "imputed_features": ["trt", "ascites"],
                },
                "error": None,
            },
            {
                "row": 1,
                "prediction": {
                    "probability": 0.994,
                    "risk_band": "high",
                    "imputed_features": [],
                },
                "error": None,
            },
        ],
    }

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return StubResponse(payload)

    monkeypatch.setattr(requests, "post", fake_post)
    return captured


def test_bulk_page_renders_without_exception():
    at = AppTest.from_file(str(BULK_PAGE), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    assert len(at.file_uploader) == 1


def test_bulk_page_scores_uploaded_csv(monkeypatch):
    captured = _stub_batch_post(monkeypatch)
    download_calls = []
    real_download_button = st.download_button

    def tracking_download_button(*args, **kwargs):
        download_calls.append((args, kwargs))
        return real_download_button(*args, **kwargs)

    monkeypatch.setattr(st, "download_button", tracking_download_button)
    at = AppTest.from_file(str(BULK_PAGE), default_timeout=60)
    at.run()
    at.file_uploader[0].set_value(("rows.csv", VALID_CSV, "text/csv")).run()
    at.button[0].click().run()

    assert not at.exception, at.exception
    assert captured["url"].endswith("/predict/batch")
    assert len(captured["json"]["rows"]) == 2
    assert captured["json"]["rows"][0]["age"] == 61.0
    assert at.dataframe
    assert len(download_calls) == 1


def test_bulk_page_rejects_unknown_columns():
    at = AppTest.from_file(str(BULK_PAGE), default_timeout=60)
    at.run()
    at.file_uploader[0].set_value(("bad.csv", UNKNOWN_COLUMN_CSV, "text/csv")).run()
    assert not at.exception, at.exception
    assert any("bilirubin" in error.value for error in at.error)
