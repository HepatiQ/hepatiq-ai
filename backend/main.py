from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List
import joblib
import numpy as np
import os


class PredictRequest(BaseModel):
    bilirubin: float = Field(..., description="Bilirubin (mg/dL)")
    albumin: float = Field(..., description="Albumin (g/dL)")
    age: float
    prothrombin_time: float = Field(..., description="Prothrombin Time (seconds)")
    platelets: float


class PredictResponse(BaseModel):
    probability: float
    shap_values: List[float]
    model_loaded: bool


app = FastAPI(title="HepatiQ API")

MODEL_PATH = os.path.join("models", "model.pkl")
_model = None


def load_model():
    global _model
    if _model is not None:
        return _model
    if os.path.exists(MODEL_PATH):
        try:
            _model = joblib.load(MODEL_PATH)
        except Exception:
            _model = None
    else:
        _model = None
    return _model


@app.on_event("startup")
def startup():
    load_model()


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    """Return a probability and placeholder SHAP values.

    If a model is saved to models/model.pkl and is compatible, it will be used.
    Otherwise a deterministic fallback score is returned so the frontend can be developed without a trained model.
    """
    model = load_model()
    x = np.array([[req.bilirubin, req.albumin, req.age, req.prothrombin_time, req.platelets]])

    if model is not None:
        # prefer predict_proba when available
        if hasattr(model, "predict_proba"):
            prob = float(model.predict_proba(x)[0, 1])
        else:
            prob = float(model.predict(x)[0])

        # attempt SHAP if available; fall back to zeros if not
        try:
            import shap
            explainer = shap.Explainer(model, feature_perturbation="interventional")
            shap_vals = explainer(x).values[0].tolist()
        except Exception:
            shap_vals = [0.0] * 5

        return PredictResponse(probability=prob, shap_values=shap_vals, model_loaded=True)

    # fallback deterministic score for local dev
    score = 0.02 * req.bilirubin - 0.1 * req.albumin + 0.03 * req.age + 0.01 * req.prothrombin_time - 0.0005 * req.platelets
    prob = 1.0 / (1.0 + np.exp(-score))
    return PredictResponse(probability=float(prob), shap_values=[0.0] * 5, model_loaded=False)
