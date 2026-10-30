"""Integrity checks for the exported `survival` datasets.

The CSVs in ``data/external`` are pinned by SHA-256 in ``PROVENANCE.json``.
Loading code and CI assert those hashes so a hand-edited or truncated CSV fails
loudly instead of silently changing model inputs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from hepatiq.paths import EXTERNAL_DATA_DIR, EXTERNAL_PROVENANCE

REGENERATE_HINT = (
    "Regenerate the external datasets with: pip install rdata && "
    "python scripts/export_r_datasets.py"
)


class DataIntegrityError(RuntimeError):
    """Raised when an external dataset is missing, corrupt, or inconsistent."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_provenance(path: Path | None = None) -> dict[str, Any]:
    provenance_path = Path(path) if path is not None else EXTERNAL_PROVENANCE
    if not provenance_path.exists():
        raise DataIntegrityError(
            f"Missing provenance file: {provenance_path}. {REGENERATE_HINT}"
        )
    return json.loads(provenance_path.read_text(encoding="utf-8"))


def verify_datasets(
    base_dir: Path | None = None,
    provenance_path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Assert every exported CSV exists and matches its pinned SHA-256.

    Returns the ``datasets`` block from the provenance file so callers can reuse
    the recorded row/column counts.
    """
    base = Path(base_dir) if base_dir is not None else EXTERNAL_DATA_DIR
    provenance = load_provenance(provenance_path)
    datasets: dict[str, dict[str, Any]] = provenance.get("datasets", {})
    if not datasets:
        raise DataIntegrityError(f"No datasets listed in {provenance_path}. {REGENERATE_HINT}")

    failures: list[str] = []
    for name, metadata in datasets.items():
        csv_path = base / metadata["file"]
        if not csv_path.exists():
            failures.append(f"{name}: missing {csv_path}")
            continue
        actual = sha256_file(csv_path)
        if actual != metadata["sha256"]:
            failures.append(
                f"{name}: sha256 {actual[:12]}… does not match pinned "
                f"{metadata['sha256'][:12]}…"
            )
    if failures:
        raise DataIntegrityError(
            "External dataset integrity check failed:\n  - "
            + "\n  - ".join(failures)
            + f"\n{REGENERATE_HINT}"
        )
    return datasets
