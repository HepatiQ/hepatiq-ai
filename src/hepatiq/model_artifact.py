"""Model artifact integrity and feature-contract checks."""

from __future__ import annotations

import hashlib
import json
import string
from collections.abc import Sequence
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA_VERSION = 1


class ModelArtifactError(RuntimeError):
    """Raised when a model artifact or its manifest cannot be trusted."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ModelArtifactError("model manifest not found")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelArtifactError("model manifest is not valid JSON") from exc
    if not isinstance(manifest, dict):
        raise ModelArtifactError("model manifest must be a JSON object")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
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

    feature_names = model.get("feature_names")
    if not isinstance(feature_names, list) or not all(isinstance(name, str) for name in feature_names):
        raise ModelArtifactError("model manifest has an invalid feature contract")

    return manifest


def verify_model_artifact(
    model_path: Path,
    manifest_path: Path,
    expected_features: Sequence[str],
) -> str:
    """Verify the artifact before loading it and return its SHA-256."""
    if not model_path.is_file():
        raise ModelArtifactError("model artifact not found")

    manifest = load_model_manifest(manifest_path)
    expected_hash = manifest["artifact"]["sha256"].lower()
    actual_hash = sha256_file(model_path)
    if actual_hash != expected_hash:
        raise ModelArtifactError("model artifact hash mismatch")

    manifest_features = manifest["model"]["feature_names"]
    if manifest_features != list(expected_features):
        raise ModelArtifactError("model manifest feature contract mismatch")

    return actual_hash


def validate_loaded_model(model: Any, expected_features: Sequence[str]) -> None:
    """Validate the loaded pipeline against the canonical feature contract."""
    expected = list(expected_features)
    feature_names = getattr(model, "feature_names_in_", None)
    if feature_names is not None and [str(name) for name in feature_names] != expected:
        raise ModelArtifactError("loaded model feature contract mismatch")

    n_features = getattr(model, "n_features_in_", None)
    if n_features is None:
        raise ModelArtifactError("loaded model does not expose a feature count")
    if int(n_features) != len(expected):
        raise ModelArtifactError("loaded model feature count mismatch")
