from __future__ import annotations
import json, numpy as np, pandas as pd
from pathlib import Path
from joblib import load
from typing import List, Dict, Any, Union

BASE = Path(__file__).resolve().parent
# Load artifacts from repository-level models_store/current
CURR = BASE.parent / "models_store" / "current"
RF  = load(CURR / "rf_koi.joblib")
CFG = json.load(open(CURR / "final_config.json", "r", encoding="utf-8"))

FEATURES: List[str] = CFG["features"]            # orden exacto de columnas de entrada al modelo
THRESHOLD: float = float(CFG.get("threshold", 0.32))

# Precompute feature medians from the current Kepler dataset for robust inference
def _load_feature_medians() -> Dict[str, float]:
    try:
        df = pd.read_csv(CURR / "kepler_clean.csv")
        df = _derive(_coerce(df))
        # Keep only known features
        cols = [c for c in FEATURES if c in df.columns]
        if not cols:
            return {}
        med = df[cols].replace([np.inf, -np.inf], np.nan).median(numeric_only=True)
        return {c: float(med.get(c)) for c in cols}
    except Exception:
        return {}

FEATURE_MEDIANS: Dict[str, float] = _load_feature_medians()

def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def _derive(df: pd.DataFrame) -> pd.DataFrame:
    # mismas derivadas usadas al entrenar (seguras si faltan)
    if {"koi_period","koi_duration","koi_depth"}.issubset(df.columns):
        with np.errstate(divide="ignore", invalid="ignore"):
            df["duty_cycle"] = df["koi_duration"] / (df["koi_period"] * 24.0)
        df["depth_frac"]  = (df["koi_depth"].clip(lower=1e-9)) * 1e-6
        df["rprstar_est"] = np.sqrt(df["depth_frac"])
    if "koi_period" in df: df["log_period"] = np.log10(df["koi_period"].clip(lower=1e-9))
    if "koi_depth"  in df: df["log_depth"]  = np.log10(df["koi_depth"].clip(lower=1e-9))
    return df

def _prepare(payload: Union[Dict[str,Any], List[Dict[str,Any]], pd.DataFrame]) -> pd.DataFrame:
    df = payload.copy() if isinstance(payload, pd.DataFrame) else pd.DataFrame(payload if isinstance(payload, list) else [payload])
    df = _derive(_coerce(df))
    # Ensure all expected columns exist
    for c in FEATURES:
        if c not in df.columns:
            df[c] = np.nan
    X = df[FEATURES].copy()
    # Replace inf and impute with medians when available
    X = X.replace([np.inf, -np.inf], np.nan)
    if FEATURE_MEDIANS:
        X = X.fillna(value={k: v for k, v in FEATURE_MEDIANS.items() if k in X.columns})
    # Any remaining NaN -> fallback to column medians of the small batch
    X = X.fillna(X.median(numeric_only=True))
    return X

def predict_one(record: Dict[str,Any], threshold: float | None = None) -> Dict[str,Any]:
    X = _prepare(record)
    p = float(RF.predict_proba(X)[:,1][0])
    thr = float(THRESHOLD if threshold is None else threshold)
    return {"probability": p, "label": int(p >= thr), "threshold": thr}

def predict_batch(records: Union[List[Dict[str,Any]], pd.DataFrame], threshold: float | None = None) -> pd.DataFrame:
    X = _prepare(records)
    proba = RF.predict_proba(X)[:,1]
    thr = float(THRESHOLD if threshold is None else threshold)
    pred = (proba >= thr).astype(int)
    out = X.copy()
    out["probability"] = proba
    out["label"] = pred
    return out