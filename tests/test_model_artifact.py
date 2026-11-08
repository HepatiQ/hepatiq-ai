"""SEC-03: model artifact integrity, safe loading, and feature-contract checks."""

import json
import shutil
from types import SimpleNamespace

import joblib
import pytest
import skops.io as sio
from fastapi.testclient import TestClient
from skops.io.exceptions import UntrustedTypesFoundException

from hepatiq.backend import main as main_module
from hepatiq.backend.main import FEATURE_COLUMNS
from hepatiq.ml import train as train_module
from hepatiq.model_artifact import (
    TRUSTED_MODEL_TYPES,
    ModelArtifactError,
    load_model,
    load_model_manifest,
    load_verified_model,
    sha256_file,
    validate_loaded_model,
    verify_model_artifact,
)
from hepatiq.paths import EXTERNAL_PBC, MODEL_MANIFEST_PATH, MODEL_PATH, PROCESSED_DATA
from tests.conftest import REQUIRED_ONLY, build_model_frame


class UnsafeProbe:
    """Serializable type that is not in the fixed allowlist or skops defaults."""


def test_manifest_matches_current_artifact():
    manifest = load_model_manifest(MODEL_MANIFEST_PATH)

    assert manifest["schema_version"] == 1
    assert manifest["artifact"]["sha256"] == sha256_file(MODEL_PATH)
    assert manifest["artifact"]["size_bytes"] == MODEL_PATH.stat().st_size
    assert manifest["model"]["feature_names"] == FEATURE_COLUMNS
    assert manifest["model"]["n_features"] == len(FEATURE_COLUMNS)
    assert manifest["model"]["pipeline_steps"] == ["imputer", "scaler", "clf"]
    assert manifest["environment"]["skops"] == "0.16.0"


def test_current_artifact_needs_only_the_expected_extra_types():
    untrusted = set(sio.get_untrusted_types(file=MODEL_PATH))

    assert untrusted == set(TRUSTED_MODEL_TYPES)


def test_skops_refuses_the_artifact_without_the_project_allowlist():
    with pytest.raises(UntrustedTypesFoundException):
        sio.load(MODEL_PATH)


def test_load_model_rejects_an_unknown_skops_type(tmp_path):
    artifact = tmp_path / "unsafe.skops"
    sio.dump(UnsafeProbe(), artifact)

    with pytest.raises(ModelArtifactError, match="could not be loaded safely"):
        load_model(artifact)


def test_verify_accepts_current_artifact():
    assert verify_model_artifact(MODEL_PATH, MODEL_MANIFEST_PATH, FEATURE_COLUMNS) == sha256_file(MODEL_PATH)


def test_load_verified_model_accepts_current_artifact():
    model, digest = load_verified_model(MODEL_PATH, MODEL_MANIFEST_PATH, FEATURE_COLUMNS)

    assert digest == sha256_file(MODEL_PATH)
    validate_loaded_model(model, FEATURE_COLUMNS)


def test_load_verified_model_rejects_manifest_model_type_mismatch(tmp_path):
    manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["model"]["type"] = "sklearn.preprocessing.StandardScaler"
    altered = tmp_path / "manifest.json"
    altered.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ModelArtifactError, match="model type does not match"):
        load_verified_model(MODEL_PATH, altered, FEATURE_COLUMNS)


def test_load_verified_model_rejects_manifest_pipeline_mismatch(tmp_path):
    manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["model"]["pipeline_steps"] = ["scaler", "imputer", "clf"]
    altered = tmp_path / "manifest.json"
    altered.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ModelArtifactError, match="pipeline does not match"):
        load_verified_model(MODEL_PATH, altered, FEATURE_COLUMNS)


def test_load_verified_model_rejects_modified_artifact(tmp_path):
    tampered = tmp_path / "model.skops"
    shutil.copyfile(MODEL_PATH, tampered)
    with tampered.open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(ModelArtifactError, match="hash mismatch"):
        load_verified_model(tampered, MODEL_MANIFEST_PATH, FEATURE_COLUMNS)


def test_load_model_rejects_a_legacy_pickle(tmp_path):
    legacy = tmp_path / "model.pkl"
    joblib.dump({"legacy": True}, legacy)

    with pytest.raises(ModelArtifactError, match="could not be loaded safely"):
        load_model(legacy)


def test_verify_rejects_missing_manifest(tmp_path):
    with pytest.raises(ModelArtifactError, match="manifest not found"):
        verify_model_artifact(MODEL_PATH, tmp_path / "missing.json", FEATURE_COLUMNS)


def test_verify_rejects_modified_artifact(tmp_path):
    tampered = tmp_path / "model.skops"
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


def test_verify_rejects_manifest_size_mismatch(tmp_path):
    manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["artifact"]["size_bytes"] += 1
    altered = tmp_path / "manifest.json"
    altered.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ModelArtifactError, match="size mismatch"):
        verify_model_artifact(MODEL_PATH, altered, FEATURE_COLUMNS)


@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda manifest: manifest.update({"schema_version": True}), "unsupported model manifest schema"),
        (lambda manifest: manifest["artifact"].update({"sha256": "not-a-hash"}), "invalid artifact hash"),
        (lambda manifest: manifest["artifact"].update({"size_bytes": True}), "invalid artifact size"),
        (lambda manifest: manifest["model"].update({"feature_names": []}), "invalid feature contract"),
        (lambda manifest: manifest["model"].update({"n_features": 16}), "invalid feature count"),
        (lambda manifest: manifest["model"].update({"pipeline_steps": "imputer"}), "invalid pipeline steps"),
        (lambda manifest: manifest["model"].update({"type": 1}), "invalid model type"),
        (lambda manifest: manifest["artifact"].update({"path": 1}), "invalid artifact path"),
    ],
)
def test_manifest_rejects_malformed_fields(tmp_path, mutate, match):
    manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))
    mutate(manifest)
    malformed = tmp_path / "manifest.json"
    malformed.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ModelArtifactError, match=match):
        load_model_manifest(malformed)


def test_verify_rejects_malformed_manifest(tmp_path):
    malformed = tmp_path / "manifest.json"
    malformed.write_text("{}", encoding="utf-8")

    with pytest.raises(ModelArtifactError, match="unsupported model manifest schema"):
        verify_model_artifact(MODEL_PATH, malformed, FEATURE_COLUMNS)


def test_validate_loaded_model_accepts_current_pipeline():
    validate_loaded_model(load_model(MODEL_PATH), FEATURE_COLUMNS)


def test_skops_artifact_preserves_frozen_prediction():
    model = load_model(MODEL_PATH)
    probability = model.predict_proba(build_model_frame(REQUIRED_ONLY))[0, 1]

    assert float(probability) == pytest.approx(0.2801766578461799, abs=1e-12)


def test_validate_loaded_model_rejects_missing_feature_names():
    model = SimpleNamespace(n_features_in_=17)

    with pytest.raises(ModelArtifactError, match="does not expose feature names"):
        validate_loaded_model(model, FEATURE_COLUMNS)


def test_validate_loaded_model_rejects_feature_contract_mismatch():
    model = SimpleNamespace(feature_names_in_=list(reversed(FEATURE_COLUMNS)), n_features_in_=17)

    with pytest.raises(ModelArtifactError, match="feature contract mismatch"):
        validate_loaded_model(model, FEATURE_COLUMNS)


def test_validate_loaded_model_rejects_feature_count_mismatch():
    model = SimpleNamespace(feature_names_in_=FEATURE_COLUMNS, n_features_in_=16)

    with pytest.raises(ModelArtifactError, match="feature count mismatch"):
        validate_loaded_model(model, FEATURE_COLUMNS)


def test_train_writes_manifest_for_artifact(tmp_path, monkeypatch):
    model_copy = tmp_path / "model.skops"
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
        pipeline=load_model(MODEL_PATH),
    )

    manifest = load_model_manifest(manifest_copy)
    assert manifest["artifact"]["sha256"] == sha256_file(MODEL_PATH)
    assert manifest["model"]["feature_names"] == FEATURE_COLUMNS
    assert manifest["training_data"]["processed"]["sha256"] == sha256_file(PROCESSED_DATA)
    assert manifest["training_data"]["source"]["rows"] == 418
    assert manifest["training"]["metrics"] == {"roc_auc": {"mean": 0.88}}
    assert manifest["environment"]["skops"] == "0.16.0"


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
