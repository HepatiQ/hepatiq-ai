"""SEC-03: model artifact integrity and feature-contract verification."""

import json
import shutil
from types import SimpleNamespace

import joblib
import pytest
from fastapi.testclient import TestClient

from hepatiq.backend import main as main_module
from hepatiq.backend.main import FEATURE_COLUMNS
from hepatiq.ml import train as train_module
from hepatiq.model_artifact import (
    ModelArtifactError,
    load_model_manifest,
    sha256_file,
    validate_loaded_model,
    verify_model_artifact,
)
from hepatiq.paths import EXTERNAL_PBC, MODEL_MANIFEST_PATH, MODEL_PATH, PROCESSED_DATA
from tests.conftest import REQUIRED_ONLY


def test_manifest_matches_current_artifact():
    manifest = load_model_manifest(MODEL_MANIFEST_PATH)

    assert manifest["schema_version"] == 1
    assert manifest["artifact"]["sha256"] == sha256_file(MODEL_PATH)
    assert manifest["artifact"]["size_bytes"] == MODEL_PATH.stat().st_size
    assert manifest["model"]["feature_names"] == FEATURE_COLUMNS
    assert manifest["model"]["n_features"] == len(FEATURE_COLUMNS)
    assert manifest["model"]["pipeline_steps"] == ["imputer", "scaler", "clf"]


def test_verify_accepts_current_artifact():
    assert verify_model_artifact(MODEL_PATH, MODEL_MANIFEST_PATH, FEATURE_COLUMNS) == sha256_file(MODEL_PATH)


def test_verify_rejects_missing_manifest(tmp_path):
    with pytest.raises(ModelArtifactError, match="manifest not found"):
        verify_model_artifact(MODEL_PATH, tmp_path / "missing.json", FEATURE_COLUMNS)


def test_verify_rejects_modified_artifact(tmp_path):
    tampered = tmp_path / "model.pkl"
    shutil.copyfile(MODEL_PATH, tampered)
    with tampered.open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(ModelArtifactError, match="hash mismatch"):
        verify_model_artifact(tampered, MODEL_MANIFEST_PATH, FEATURE_COLUMNS)


def test_verify_rejects_manifest_feature_mismatch(tmp_path):
    manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["model"]["feature_names"] = list(reversed(FEATURE_COLUMNS))
    altered = tmp_path / "manifest.json"
    altered.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ModelArtifactError, match="feature contract mismatch"):
        verify_model_artifact(MODEL_PATH, altered, FEATURE_COLUMNS)


def test_verify_rejects_malformed_manifest(tmp_path):
    malformed = tmp_path / "manifest.json"
    malformed.write_text("{}", encoding="utf-8")

    with pytest.raises(ModelArtifactError, match="unsupported model manifest schema"):
        verify_model_artifact(MODEL_PATH, malformed, FEATURE_COLUMNS)


def test_validate_loaded_model_accepts_current_pipeline():
    validate_loaded_model(joblib.load(MODEL_PATH), FEATURE_COLUMNS)


def test_validate_loaded_model_rejects_feature_contract_mismatch():
    model = SimpleNamespace(feature_names_in_=list(reversed(FEATURE_COLUMNS)), n_features_in_=17)

    with pytest.raises(ModelArtifactError, match="feature contract mismatch"):
        validate_loaded_model(model, FEATURE_COLUMNS)


def test_validate_loaded_model_rejects_feature_count_mismatch():
    model = SimpleNamespace(feature_names_in_=FEATURE_COLUMNS, n_features_in_=16)

    with pytest.raises(ModelArtifactError, match="feature count mismatch"):
        validate_loaded_model(model, FEATURE_COLUMNS)


def test_train_writes_manifest_for_artifact(tmp_path, monkeypatch):
    model_copy = tmp_path / "model.pkl"
    processed_copy = tmp_path / "processed.csv"
    source_copy = tmp_path / "pbc.csv"
    manifest_copy = tmp_path / "manifest.json"
    shutil.copyfile(MODEL_PATH, model_copy)
    shutil.copyfile(PROCESSED_DATA, processed_copy)
    shutil.copyfile(EXTERNAL_PBC, source_copy)

    monkeypatch.setattr(train_module, "MODEL_PATH", model_copy)
    monkeypatch.setattr(train_module, "PROCESSED_DATA", processed_copy)
    monkeypatch.setattr(train_module, "EXTERNAL_PBC", source_copy)
    monkeypatch.setattr(train_module, "MODEL_MANIFEST_PATH", manifest_copy)

    metrics_out = {
        "cohort_size": 329,
        "class_balance": {"severe_event=0": 197, "severe_event=1": 132},
        "cv_folds": 5,
        "results": {"logistic_regression": {"roc_auc": {"mean": 0.88}}},
    }
    train_module.write_model_manifest(
        winner_name="logistic_regression",
        winner_reason="test",
        feature_names=FEATURE_COLUMNS,
        metrics_out=metrics_out,
        pipeline=joblib.load(MODEL_PATH),
    )

    manifest = load_model_manifest(manifest_copy)
    assert manifest["artifact"]["sha256"] == sha256_file(MODEL_PATH)
    assert manifest["model"]["feature_names"] == FEATURE_COLUMNS
    assert manifest["training_data"]["processed"]["sha256"] == sha256_file(PROCESSED_DATA)
    assert manifest["training_data"]["source"]["rows"] == 418
    assert manifest["training"]["metrics"] == {"roc_auc": {"mean": 0.88}}


def test_app_fails_closed_when_manifest_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HEPATIQ_DB_PATH", str(tmp_path / "test_history.db"))
    monkeypatch.setattr(main_module, "MODEL_MANIFEST_PATH", tmp_path / "missing.json")

    with TestClient(main_module.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["model_loaded"] is False
        assert health.json()["error"] == "model unavailable"
        assert str(tmp_path) not in health.text

        prediction = client.post("/predict", json=REQUIRED_ONLY)
        assert prediction.status_code == 503
        assert prediction.json()["detail"] == "Model not loaded"
        assert str(tmp_path) not in prediction.text
