"""Simple, non-PBC-specific liver scores used as comparators.

Neither score was developed for PBC, so they are included as generic
biomarker-only baselines rather than as clinical standards.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

BILIRUBIN_MGDL_TO_UMOL = 17.1
ALBUMIN_GDL_TO_GL = 10.0
AST_UPPER_LIMIT = 40.0


def albi_score(bili_mgdl: pd.Series | np.ndarray, albumin_gdl: pd.Series | np.ndarray) -> pd.Series:
    """ALBI grade score: higher (less negative) means worse liver function."""
    bili_umol = np.asarray(bili_mgdl, dtype=float) * BILIRUBIN_MGDL_TO_UMOL
    albumin_gl = np.asarray(albumin_gdl, dtype=float) * ALBUMIN_GDL_TO_GL
    with np.errstate(divide="ignore", invalid="ignore"):
        score = np.log10(bili_umol) * 0.66 + albumin_gl * (-0.085)
    return pd.Series(score, index=getattr(bili_mgdl, "index", None), name="albi")


def albi_grade(score: pd.Series | np.ndarray) -> pd.Series:
    """ALBI grade 1 (<= -2.60), 2 (<= -1.39) or 3."""
    values = np.asarray(score, dtype=float)
    grades = np.where(values <= -2.60, 1, np.where(values <= -1.39, 2, 3))
    grades = np.where(np.isfinite(values), grades, np.nan)
    return pd.Series(grades, index=getattr(score, "index", None), name="albi_grade")


def apri_score(
    ast: pd.Series | np.ndarray,
    platelet: pd.Series | np.ndarray,
    ast_upper_limit: float = AST_UPPER_LIMIT,
) -> pd.Series:
    """AST-to-platelet ratio index: higher means more fibrosis."""
    ast_values = np.asarray(ast, dtype=float)
    platelets = np.asarray(platelet, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        score = (ast_values / ast_upper_limit) * 100.0 / platelets
    return pd.Series(score, index=getattr(ast, "index", None), name="apri")
