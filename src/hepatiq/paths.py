"""Central path resolution for HepatiQ.

Every module that reads the dataset, loads a model, writes a report, or opens
the history database should import its path from here. This keeps the repo
layout in one place and lets deployments override locations via environment
variables without touching code.
"""

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "data").is_dir():
            return candidate
    return Path.cwd()


REPO_ROOT = Path(os.environ.get("HEPATIQ_ROOT") or _find_repo_root(PACKAGE_DIR))

DATA_DIR = REPO_ROOT / "data"
RAW_DATA = DATA_DIR / "raw" / "pbc.csv"
PROCESSED_DATA = DATA_DIR / "processed" / "pbc_5yr_target.csv"
INTERIM_DIR = DATA_DIR / "interim"

EXTERNAL_DATA_DIR = DATA_DIR / "external"
EXTERNAL_PBC = EXTERNAL_DATA_DIR / "pbc.csv"
EXTERNAL_PBCSEQ = EXTERNAL_DATA_DIR / "pbcseq.csv"
EXTERNAL_UDCA = EXTERNAL_DATA_DIR / "udca.csv"
EXTERNAL_UDCA1 = EXTERNAL_DATA_DIR / "udca1.csv"
EXTERNAL_UDCA2 = EXTERNAL_DATA_DIR / "udca2.csv"
EXTERNAL_PROVENANCE = EXTERNAL_DATA_DIR / "PROVENANCE.json"

MODELS_DIR = Path(os.environ.get("HEPATIQ_MODELS_DIR") or REPO_ROOT / "models")
MODEL_PATH = MODELS_DIR / "model.pkl"
CANDIDATES_DIR = MODELS_DIR / "candidates"
METRICS_PATH = CANDIDATES_DIR / "training_metrics.json"

DEFAULT_DB_PATH = Path(os.environ.get("HEPATIQ_DB_PATH") or DATA_DIR / "hepatiq.db")

VALIDATION_DIR = PACKAGE_DIR / "validation"
VALIDATION_REPORT_PATH = VALIDATION_DIR / "report.md"
CALIBRATION_PLOT_PATH = VALIDATION_DIR / "calibration_plot.png"
