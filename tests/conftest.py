"""Shared fixtures for the HepatiQ test suite."""

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import joblib  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.main import FEATURE_COLUMNS, MODEL_PATH, app  # noqa: E402

REQUIRED_ONLY = {"age": 58.0, "sex": "f", "edema": 0.0, "bili": 1.2, "albumin": 3.6}

SAMPLE_FULL = {
    "trt": 1.0, "age": 58.0, "sex": "f", "ascites": 0.0, "hepato": 1.0,
    "spiders": 0.0, "edema": 0.0, "bili": 1.2, "chol": 300.0, "albumin": 3.6,
    "copper": 30.0, "alk_phos": 800.0, "ast": 80.0, "trig": 120.0,
    "platelet": 250.0, "protime": 11.0, "stage": 2.0,
}

OLD_5FEATURE = {
    "bilirubin": 1.2, "albumin": 3.6, "age": 58.0,
    "prothrombin_time": 11.0, "platelets": 250.0,
}


def build_model_frame(payload: dict) -> pd.DataFrame:
    """Replicate exactly what backend.main builds, for joblib parity checks."""
    row = {}
    for feature in FEATURE_COLUMNS:
        if feature == "sex":
            row[feature] = 0.0 if payload["sex"].lower() == "f" else 1.0
            continue
        api_name = "alk_phos" if feature == "alk.phos" else feature
        value = payload.get(api_name)
        row[feature] = float(value) if value is not None else float("nan")
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HEPATIQ_DB_PATH", str(tmp_path / "test_history.db"))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def model():
    return joblib.load(MODEL_PATH)
