"""Model artifact integrity, safe deserialization, and feature-contract checks."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import string
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import skops.io as sio

MANIFEST_SCHEMA_VERSION = 1

# Deliberately hard-coded. These are the extra types the current artifact needs
# beyond skops' library-controlled default trusted set. Never derive this list
# from the artifact being loaded; doing so defeats the purpose of the check.
TRUSTED_MODEL_TYPES = (
    "numpy.dtype",
    "sklearn.impute._iterative.IterativeImputer",
    "sklearn.impute._iterative._ImputerTriplet",
)


class ModelArtifactError(RuntimeError):
    """Raised when a model artifact or its manifest cannot be trusted."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_artifact(path: Path) -> bytes:
    if not path.is_file():
        raise ModelArtifactError("model artifact not found")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ModelArtifactError("model artifact could not be read") from exc


def load_model_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ModelArtifactError("model manifest not found")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelArtifactError("model manifest is not valid JSON") from exc
    if not isinstance(manifest, dict):
        raise ModelArtifactError("model manifest must be a JSON object")
    schema_version = manifest.get("schema_version")
    if type(schema_version) is not int or schema_version != MANIFEST_SCHEMA_VERSION:
        raise ModelArtifactError("unsupported model manifest schema")

    artifact = manifest.get("artifact")
    model = manifest.get("model")
    if not isinstance(artifact, dict) or not isinstance(model, dict):
        raise ModelArtifactError("model manifest is missing required sections")

    artifact_hash = artifact.get("sha256")
    if (
        not isinstance(artifact_hash, str)
        or len(artifact_hash) != 64
        or any(char not in string.hexdigits for char in artifact_hash)
    ):
        raise ModelArtifactError("model manifest has an invalid artifact hash")

    size_bytes = artifact.get("size_bytes")
    if size_bytes is not None and (type(size_bytes) is not int or size_bytes <= 0):
        raise ModelArtifactError("model manifest has an invalid artifact size")

    feature_names = model.get("feature_names")
    if (
        not isinstance(feature_names, list)
        or not feature_names
        or not all(isinstance(name, str) and name for name in feature_names)
        or len(set(feature_names)) != len(feature_names)
    ):
        raise ModelArtifactError("model manifest has an invalid feature contract")

    n_features = model.get("n_features")
    if n_features is not None and (type(n_features) is not int or n_features != len(feature_names)):
        raise ModelArtifactError("model manifest has an invalid feature count")

    pipeline_steps = model.get("pipeline_steps")
    if pipeline_steps is not None and (
        not isinstance(pipeline_steps, list)
        or not all(isinstance(step, str) and step for step in pipeline_steps)
    ):
        raise ModelArtifactError("model manifest has invalid pipeline steps")

    model_type = model.get("type")
    if model_type is not None and not isinstance(model_type, str):
        raise ModelArtifactError("model manifest has an invalid model type")

    artifact_path = artifact.get("path")
    if artifact_path is not None and not isinstance(artifact_path, str):
        raise ModelArtifactError("model manifest has an invalid artifact path")

    return manifest


def _verify_artifact_bytes(
    data: bytes,
    manifest: dict[str, Any],
    expected_features: Sequence[str],
) -> str:
    expected_hash = manifest["artifact"]["sha256"].lower()
    actual_hash = sha256_bytes(data)
    if not hmac.compare_digest(actual_hash, expected_hash):
        raise ModelArtifactError("model artifact hash mismatch")

    expected_size = manifest["artifact"].get("size_bytes")
    if expected_size is not None and expected_size != len(data):
        raise ModelArtifactError("model artifact size mismatch")

    manifest_features = manifest["model"]["feature_names"]
    if manifest_features != list(expected_features):
        raise ModelArtifactError("model manifest feature contract mismatch")

    return actual_hash


def verify_model_artifact(
    model_path: Path,
    manifest_path: Path,
    expected_features: Sequence[str],
) -> str:
    """Verify the artifact before loading it and return its SHA-256."""
    data = _read_artifact(model_path)
    manifest = load_model_manifest(manifest_path)
    return _verify_artifact_bytes(data, manifest, expected_features)


def load_model(model_path: Path) -> Any:
    """Load a skops artifact using the fixed extra trusted-type allowlist."""
    data = _read_artifact(model_path)
    try:
        return sio.load(io.BytesIO(data), trusted=TRUSTED_MODEL_TYPES)
    except Exception as exc:
        raise ModelArtifactError("model artifact could not be loaded safely") from exc


def dump_model(model: Any, model_path: Path) -> None:
    """Serialize the deployed model with skops rather than pickle/joblib."""
    sio.dump(
        model,
        model_path,
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    )


def load_verified_model(
    model_path: Path,
    manifest_path: Path,
    expected_features: Sequence[str],
) -> tuple[Any, str]:
    """Verify and load from the same byte snapshot, then validate the pipeline."""
    data = _read_artifact(model_path)
    manifest = load_model_manifest(manifest_path)
    actual_hash = _verify_artifact_bytes(data, manifest, expected_features)

    try:
        model = sio.load(io.BytesIO(data), trusted=TRUSTED_MODEL_TYPES)
    except Exception as exc:
        raise ModelArtifactError("model artifact could not be loaded safely") from exc

    validate_loaded_model(model, expected_features)
    _validate_manifest_model(manifest, model)
    return model, actual_hash


def _validate_manifest_model(manifest: dict[str, Any], model: Any) -> None:
    """Ensure the loaded object matches the manifest's model description."""
    model_meta = manifest["model"]

    model_type = model_meta.get("type")
    if model_type is not None:
        actual_type = f"{type(model).__module__}.{type(model).__name__}"
        if actual_type != model_type:
            raise ModelArtifactError("loaded model type does not match manifest")

    pipeline_steps = model_meta.get("pipeline_steps")
    if pipeline_steps is not None:
        named_steps = getattr(model, "named_steps", None)
        if named_steps is None or list(named_steps) != pipeline_steps:
            raise ModelArtifactError("loaded model pipeline does not match manifest")


def validate_loaded_model(model: Any, expected_features: Sequence[str]) -> None:
    """Validate the loaded pipeline against the canonical feature contract."""
    expected = list(expected_features)
    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is None:
        raise ModelArtifactError("loaded model does not expose feature names")
    if [str(name) for name in feature_names] != expected:
        raise ModelArtifactError("loaded model feature contract mismatch")

    n_features = getattr(model, "n_features_in_", None)
    if n_features is None:
        raise ModelArtifactError("loaded model does not expose a feature count")
    if int(n_features) != len(expected):
        raise ModelArtifactError("loaded model feature count mismatch")
