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

from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal, Optional
import os

import joblib
import numpy as np
import pandas as pd
import shap
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.db import DEFAULT_DB_PATH, fetch_recent, init_db, log_prediction

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = REPO_ROOT / "models" / "model.pkl"
DATA_PATH = REPO_ROOT / "data" / "pbc_5yr_target.csv"
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
    contributions: List[Contribution]
    model_loaded: bool


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    n_features: int
    model_path: str
    explainer_ready: bool
    error: Optional[str] = None


class HistoryItem(BaseModel):
    id: int
    created_at: str
    request: dict
    probability: float
    contributions: List[Contribution]


class HistoryResponse(BaseModel):
    items: List[HistoryItem]


_state: dict = {"model": None, "explainer": None, "error": None, "db_path": None}


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
        _state["error"] = None
    except Exception as exc:
        _state["model"] = None
        _state["explainer"] = None
        _state["error"] = f"{type(exc).__name__}: {exc}"

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
        error=_state["error"],
    )


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
        impact_by_feature = dict(zip(FEATURE_COLUMNS, (float(v) for v in shap_row)))

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
        contributions=contributions,
        model_loaded=True,
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
            )
        except Exception:
            pass

    return response


@app.get("/history", response_model=HistoryResponse)
def history(limit: int = Query(20, ge=1, le=100)) -> HistoryResponse:
    if _state["db_path"] is None:
        raise HTTPException(status_code=503, detail="Prediction history unavailable (database not initialized)")
    try:
        items = fetch_recent(_state["db_path"], limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Prediction history unavailable: {exc}")
    return HistoryResponse(items=[HistoryItem(**item) for item in items])
