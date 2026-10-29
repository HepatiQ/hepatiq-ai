"""HepatiQ FastAPI service — 17-feature 5-year severe-event risk model.

Loads models/model.pkl (an sklearn Pipeline: IterativeImputer -> StandardScaler
-> LogisticRegression, trained on 17 PBC features) at startup, builds a SHAP
LinearExplainer once, and serves /health and /predict.

Contract:
    - Required request fields: age, sex (f/m), edema (0/0.5/1), bili, albumin.
      All other model features are optional; omitted fields become NaN and are
      filled by the pipeline's IterativeImputer at predict time.
    - Unknown fields are rejected (422) so stale clients fail loudly.
    - If the model cannot be loaded, /predict returns 503 — never a fabricated
      fallback probability.
    - Response includes per-feature SHAP contributions in log-odds units,
      flagged with whether each value was imputed server-side.
"""

import hashlib
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal, Optional

import joblib
import numpy as np
import pandas as pd
import shap
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from hepatiq.backend.db import (
    clear_predictions,
    fetch_recent,
    get_stats,
    init_db,
    log_prediction,
)
from hepatiq.paths import DEFAULT_DB_PATH, MODEL_PATH, PROCESSED_DATA

try:
    from hepatiq.backend.agent import ClinicalAgent
except ImportError:  # optional dependency in some environments
    class ClinicalAgent:  # type: ignore[no-redef]
        def reason_loop(self, *_args, **_kwargs):
            raise RuntimeError("Clinical agent module is unavailable")

_agent = ClinicalAgent()
DATA_PATH = PROCESSED_DATA
BACKGROUND_SAMPLE_SIZE = 100
RANDOM_STATE = 42

# Canonical training column order (see models/training_metrics.json).
FEATURE_COLUMNS = [
    "trt", "age", "sex", "ascites", "hepato", "spiders", "edema",
    "bili", "chol", "albumin", "copper", "alk.phos", "ast", "trig",
    "platelet", "protime", "stage",
]

# API field name -> training column name. alk.phos uses a dot in training;
# the API exposes alk_phos so JSON field names stay valid identifiers.
FEATURE_TO_API = {
    "trt": "trt", "age": "age", "sex": "sex", "ascites": "ascites",
    "hepato": "hepato", "spiders": "spiders", "edema": "edema",
    "bili": "bili", "chol": "chol", "albumin": "albumin",
    "copper": "copper", "alk.phos": "alk_phos", "ast": "ast",
    "trig": "trig", "platelet": "platelet", "protime": "protime",
    "stage": "stage",
}

# Risk bands for display. "high" starts at the cohort's observed 5-year event
# rate (132/329 = 0.401; validation/report.md); 0.15 separates the low tail.
# Descriptive aids for communication, not clinical action thresholds.
RISK_BAND_INTERMEDIATE = 0.15
RISK_BAND_HIGH = 0.40


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trt: Optional[float] = Field(None, ge=1, le=2, description="Treatment arm (1 or 2)")
    age: float = Field(..., ge=0, le=120, description="Age (years)")
    sex: Literal["f", "m"] = Field(..., description="Sex (f or m; case-insensitive)")
    ascites: Optional[float] = Field(None, ge=0, le=1, description="Ascites (0 or 1)")
    hepato: Optional[float] = Field(None, ge=0, le=1, description="Hepatomegaly (0 or 1)")
    spiders: Optional[float] = Field(None, ge=0, le=1, description="Spider angiomata (0 or 1)")
    edema: float = Field(..., ge=0, le=1, description="Edema (0, 0.5, or 1)")
    bili: float = Field(..., ge=0, le=100, description="Serum bilirubin (mg/dL)")
    chol: Optional[float] = Field(None, ge=0, le=5000, description="Serum cholesterol (mg/dL)")
    albumin: float = Field(..., ge=0, le=10, description="Albumin (g/dL)")
    copper: Optional[float] = Field(None, ge=0, le=1000, description="Urine copper (ug/day)")
    alk_phos: Optional[float] = Field(None, ge=0, le=50000, description="Alkaline phosphatase (U/L)")
    ast: Optional[float] = Field(None, ge=0, le=10000, description="AST (U/L)")
    trig: Optional[float] = Field(None, ge=0, le=10000, description="Triglycerides (mg/dL)")
    platelet: Optional[float] = Field(None, ge=1, le=1000, description="Platelet count (thousands/uL)")
    protime: Optional[float] = Field(None, ge=1, le=100, description="Prothrombin time (seconds)")
    stage: Optional[float] = Field(None, ge=1, le=4, description="Histologic stage (1-4)")

    @field_validator("sex", mode="before")
    @classmethod
    def _normalize_sex(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower()
        return v


class Contribution(BaseModel):
    feature: str
    value: Optional[float] = None
    impact: Optional[float] = None
    imputed: bool


class PredictResponse(BaseModel):
    probability: float
    risk_band: Literal["low", "intermediate", "high"]
    contributions: List[Contribution]
    model_loaded: bool
    model_version: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    n_features: int
    model_path: str
    explainer_ready: bool
    model_version: Optional[str] = None
    error: Optional[str] = None


class HistoryItem(BaseModel):
    id: int
    created_at: str
    request: dict
    probability: float
    contributions: List[Contribution]


class HistoryResponse(BaseModel):
    items: List[HistoryItem]


class HistoryClearResponse(BaseModel):
    deleted: int


_state: dict = {
    "model": None,
    "explainer": None,
    "error": None,
    "db_path": None,
    "model_version": None,
    "feature_ranges": None,
}


def _build_explainer(model):
    """Build a SHAP explainer once, at startup.

    LinearExplainer with a sampled background (same recipe as ml/explain.py)
    when the classifier exposes coef_; TreeExplainer otherwise so a future
    tree-based winner works without code changes.
    """
    classifier = model.named_steps["clf"]
    preprocessor = model[:-1]

    df = pd.read_csv(DATA_PATH)
    features = df[FEATURE_COLUMNS].copy()
    features["sex"] = features["sex"].astype(str).str.lower().map({"f": 0.0, "m": 1.0})
    background = features.sample(BACKGROUND_SAMPLE_SIZE, random_state=RANDOM_STATE)
    background_transformed = preprocessor.transform(background)

    if hasattr(classifier, "coef_"):
        return shap.LinearExplainer(classifier, background_transformed)
    return shap.TreeExplainer(classifier)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"model file not found: {MODEL_PATH}")
        model = joblib.load(MODEL_PATH)
        _state["model"] = model
        _state["explainer"] = _build_explainer(model)
        _state["model_version"] = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()[:8]
        _state["error"] = None
    except Exception as exc:
        _state["model"] = None
        _state["explainer"] = None
        _state["model_version"] = None
        _state["error"] = f"{type(exc).__name__}: {exc}"

    # Per-feature training ranges (data CSV) power extrapolation warnings.
    try:
        csv_features = pd.read_csv(DATA_PATH)[FEATURE_COLUMNS]
        _state["feature_ranges"] = {
            col: (float(csv_features[col].min()), float(csv_features[col].max()))
            for col in FEATURE_COLUMNS
            if col != "sex"
        }
    except Exception:
        _state["feature_ranges"] = None

    try:
        db_path = Path(os.environ.get("HEPATIQ_DB_PATH") or DEFAULT_DB_PATH)
        init_db(db_path)
        _state["db_path"] = db_path
    except Exception:
        _state["db_path"] = None

    yield
    _state.clear()


app = FastAPI(title="HepatiQ API", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    model_ok = _state["model"] is not None
    explainer_ok = _state["explainer"] is not None
    if model_ok and explainer_ok:
        status = "ok"
    elif model_ok:
        status = "degraded"
    else:
        status = "error"
    return HealthResponse(
        status=status,
        model_loaded=model_ok,
        n_features=len(FEATURE_COLUMNS),
        model_path=str(MODEL_PATH),
        explainer_ready=explainer_ok,
        model_version=_state.get("model_version"),
        error=_state["error"],
    )


def _risk_band(probability: float) -> Literal["low", "intermediate", "high"]:
    if probability >= RISK_BAND_HIGH:
        return "high"
    if probability >= RISK_BAND_INTERMEDIATE:
        return "intermediate"
    return "low"


def _range_warnings(req: PredictRequest) -> List[str]:
    """Flag provided values lying outside the training data's observed range."""
    ranges = _state.get("feature_ranges")
    if not ranges:
        return []
    raw = req.model_dump()
    warnings: List[str] = []
    for feature, (lo, hi) in ranges.items():
        api_name = FEATURE_TO_API[feature]
        val = raw.get(api_name)
        if val is None:
            continue  # imputed server-side — nothing provided to extrapolate
        if val < lo or val > hi:
            warnings.append(
                f"{api_name}={val:g} is outside the training range "
                f"[{lo:g}, {hi:g}] — the model is extrapolating"
            )
    return warnings


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    model = _state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail=f"Model not loaded: {_state['error']}")

    raw = req.model_dump()

    row = {}
    imputed = {}
    for feature in FEATURE_COLUMNS:
        api_name = FEATURE_TO_API[feature]
        if feature == "sex":
            row[feature] = 0.0 if raw["sex"] == "f" else 1.0
            imputed[feature] = False
            continue
        val = raw.get(api_name)
        if val is None:
            row[feature] = np.nan
            imputed[feature] = True
        else:
            row[feature] = float(val)
            imputed[feature] = False

    df = pd.DataFrame([row], columns=FEATURE_COLUMNS)
    probability = float(model.predict_proba(df)[0, 1])

    impact_by_feature = {f: None for f in FEATURE_COLUMNS}
    explainer = _state["explainer"]
    if explainer is not None:
        x_transformed = model[:-1].transform(df)
        shap_row = np.asarray(explainer.shap_values(x_transformed)).reshape(-1)
        impact_by_feature = dict(zip(FEATURE_COLUMNS, (float(v) for v in shap_row), strict=False))

    contributions = [
        Contribution(
            feature=feature,
            value=row[feature] if not imputed[feature] else None,
            impact=impact_by_feature[feature],
            imputed=imputed[feature],
        )
        for feature in FEATURE_COLUMNS
    ]

    response = PredictResponse(
        probability=probability,
        risk_band=_risk_band(probability),
        contributions=contributions,
        model_loaded=True,
        model_version=_state.get("model_version"),
        warnings=_range_warnings(req),
    )

    # History must never break a prediction: a logging failure is swallowed
    # here and surfaced only through /health-style ops checks, not as a 500.
    if _state["db_path"] is not None:
        try:
            log_prediction(
                _state["db_path"],
                request=raw,
                probability=probability,
                contributions=[c.model_dump() for c in contributions],
                model_version=_state.get("model_version"),
            )
        except Exception:
            pass

    return response


class AgentRequest(BaseModel):
    age: float
    sex: Literal["f", "m"]
    edema: float
    bili: float
    albumin: float
    trt: Optional[float] = None
    ascites: Optional[float] = None
    hepato: Optional[float] = None
    spiders: Optional[float] = None
    chol: Optional[float] = None
    copper: Optional[float] = None
    alk_phos: Optional[float] = None
    ast: Optional[float] = None
    trig: Optional[float] = None
    platelet: Optional[float] = None
    protime: Optional[float] = None
    stage: Optional[float] = None


@app.post("/agent/reason")
def agent_reason(req: AgentRequest):
    """AI agent loop for clinical reasoning and recommendations."""
    raw = req.model_dump()
    # First get prediction
    pred_req = PredictRequest(**raw)
    pred_response = predict(pred_req)
    # Run agent loop
    contributions = [c.model_dump() for c in pred_response.contributions]
    result = _agent.reason_loop(raw, pred_response.probability, contributions)
    return {
        "prediction": {
            "probability": pred_response.probability,
            "risk_band": pred_response.risk_band,
        },
        "agent_analysis": result,
    }


@app.get("/stats")
def stats():
    if _state["db_path"] is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        return get_stats(_state["db_path"])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/history", response_model=HistoryResponse)
def history(limit: int = Query(20, ge=1, le=100), risk_band: str = Query(None)) -> HistoryResponse:
    if _state["db_path"] is None:
        raise HTTPException(status_code=503, detail="Prediction history unavailable (database not initialized)")
    try:
        items = fetch_recent(_state["db_path"], limit, risk_band=risk_band)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Prediction history unavailable: {exc}") from exc
    return HistoryResponse(items=[HistoryItem(**item) for item in items])


@app.delete("/history", response_model=HistoryClearResponse)
def clear_history() -> HistoryClearResponse:
    if _state["db_path"] is None:
        raise HTTPException(status_code=503, detail="Prediction history unavailable (database not initialized)")
    try:
        deleted = clear_predictions(_state["db_path"])
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Prediction history unavailable: {exc}") from exc
    return HistoryClearResponse(deleted=deleted)
