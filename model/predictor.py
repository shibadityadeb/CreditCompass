"""
model/predictor.py
------------------
Shared ML model wrapper for CreditCompass.
Loads the trained XGBoost model and exposes a predict() function
used by both the /predict (Milestone 1) and /assess (Milestone 2) endpoints.
"""

import os
import logging
import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

MODEL_PATH = os.environ.get("MODEL_PATH", "xgb_credit_model.pkl")

# Feature order must match the order used during model training
FEATURE_ORDER = [
    "rev_util", "age", "late_30_59", "debt_ratio", "monthly_inc",
    "open_credit", "late_90", "real_estate", "late_60_89", "dependents"
]

# Median defaults from the Give Me Some Credit training dataset.
# Used when a borrower field is missing so the ML model can still run.
FEATURE_DEFAULTS = {
    "rev_util":    0.154,
    "age":         52,
    "late_30_59":  0,
    "debt_ratio":  0.336,
    "monthly_inc": 5400.0,
    "open_credit": 8,
    "late_90":     0,
    "real_estate": 1,
    "late_60_89":  0,
    "dependents":  0,
}

# Singleton model instance — loaded once and reused
_model = None


# ─────────────────────────────────────────────────────────────────────────────
# Model Loading
# ─────────────────────────────────────────────────────────────────────────────

def get_model():
    """Load model from disk if not already loaded (lazy singleton)."""
    global _model
    if _model is None:
        try:
            _model = joblib.load(MODEL_PATH)
            logger.info(f"[Predictor] Model loaded from {MODEL_PATH}")
        except FileNotFoundError:
            logger.error(f"[Predictor] Model file not found: {MODEL_PATH}")
            raise
        except Exception as e:
            logger.error(f"[Predictor] Error loading model: {e}")
            raise
    return _model


# ─────────────────────────────────────────────────────────────────────────────
# Prediction
# ─────────────────────────────────────────────────────────────────────────────

def predict(borrower_data: dict) -> dict:
    """
    Run the XGBoost model on borrower data.

    Missing fields are filled with dataset medians so the model can still
    produce a prediction (with a cautionary note in the report).

    Args:
        borrower_data: dict with any subset of FEATURE_ORDER keys

    Returns:
        dict with:
            probability      – raw float (0–1)
            probability_pct  – percentage rounded to 2 dp
            risk_level       – "Low Risk" / "Medium Risk" / "High Risk"
            risk_class       – "low" / "medium" / "high"
            used_defaults    – list of field names that fell back to defaults
    """
    model = get_model()

    filled_data = {}
    used_defaults = []

    for feature in FEATURE_ORDER:
        value = borrower_data.get(feature)
        if value is None or (isinstance(value, float) and np.isnan(value)):
            filled_data[feature] = FEATURE_DEFAULTS[feature]
            used_defaults.append(feature)
        else:
            filled_data[feature] = float(value)

    df = pd.DataFrame([filled_data])[FEATURE_ORDER]
    probability = float(model.predict_proba(df)[0][1])

    # Risk classification thresholds
    if probability > 0.70:
        risk_level, risk_class = "High Risk", "high"
    elif probability > 0.40:
        risk_level, risk_class = "Medium Risk", "medium"
    else:
        risk_level, risk_class = "Low Risk", "low"

    return {
        "probability":     round(probability, 4),
        "probability_pct": round(probability * 100, 2),
        "risk_level":      risk_level,
        "risk_class":      risk_class,
        "used_defaults":   used_defaults,
    }
