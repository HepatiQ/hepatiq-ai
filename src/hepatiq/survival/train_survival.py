"""Train and evaluate the research-only v2 Cox survival baseline.

Run:
    python -m hepatiq.survival.train_survival

Outputs:
    models/candidates/survival_cox.json
    models/candidates/survival_metrics.json

The serving artifact (``models/model.skops``) is deliberately untouched. This
experiment only promotes a new model if it clears the predeclared out-of-fold
Harrell C-index bar in ``hepatiq.survival.evaluation``.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from hepatiq.data import build_survival_cohort, verify_datasets
from hepatiq.data.provenance import sha256_file
from hepatiq.paths import (
    CANDIDATES_DIR,
    REPO_ROOT,
    SURVIVAL_METRICS_PATH,
    SURVIVAL_MODEL_PATH,
)
from hepatiq.survival.evaluation import (
    cross_validate_survival,
    cross_validate_v1_baseline,
    evaluate_survival_comparison,
)
from hepatiq.survival.model import (
    MODEL_PARAMS,
    SURVIVAL_FEATURES,
    fit_survival_model,
    survival_feature_frame,
    survival_labels,
)


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.generic):
        return _json_ready(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def main() -> int:
    cohort = build_survival_cohort()
    survival_result = cross_validate_survival(cohort)
    baseline_result = cross_validate_v1_baseline(cohort)
    report = evaluate_survival_comparison(
        cohort,
        survival_result=survival_result,
        baseline_result=baseline_result,
    )

    features = survival_feature_frame(cohort)
    duration, event = survival_labels(cohort)
    final_model = fit_survival_model(features, duration, event)

    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    final_model.estimator.save_model(str(SURVIVAL_MODEL_PATH))

    report["model"] = {
        "type": "xgboost.XGBRegressor",
        "objective": MODEL_PARAMS["objective"],
        "params": MODEL_PARAMS,
        "features": list(SURVIVAL_FEATURES),
    }
    report["sources"] = verify_datasets()
    report["artifact"] = {
        "path": _relative(SURVIVAL_MODEL_PATH),
        "sha256": sha256_file(SURVIVAL_MODEL_PATH),
        "size_bytes": SURVIVAL_MODEL_PATH.stat().st_size,
    }
    report["generated_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    SURVIVAL_METRICS_PATH.write_text(
        json.dumps(_json_ready(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    survival_c = report["survival"]["c_index"]
    baseline_c = report["baseline"]["c_index"]
    survival_auc = report["survival"]["five_year"]["auc"]
    baseline_auc = report["baseline"]["five_year"]["auc"]
    print(f"Survival Cox: C-index {survival_c['point']:.3f} "
          f"[{survival_c['lower']:.3f}, {survival_c['upper']:.3f}], "
          f"5y AUC {survival_auc['point']:.3f}")
    print(f"v1 baseline:  C-index {baseline_c['point']:.3f} "
          f"[{baseline_c['lower']:.3f}, {baseline_c['upper']:.3f}], "
          f"5y AUC {baseline_auc['point']:.3f}")
    print(
        f"Promote to serving: {report['comparison']['promote_to_serving']} "
        f"(delta C-index {report['comparison']['delta_c_index']:+.3f})"
    )
    print(f"Model -> {SURVIVAL_MODEL_PATH}")
    print(f"Metrics -> {SURVIVAL_METRICS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
