from __future__ import annotations
"""
Reentrenamiento offline 60/20/20 con versionado de artefactos.

Entrena RandomForest con:
- n_estimators=500, max_depth=12, min_samples_leaf=5, max_features="sqrt"

Deriva las mismas variables usadas en inferencia y guarda artefactos en:
  app/models_store/versions/{timestamp}/
Si activate=True, copia también a:
  app/models_store/current/

Umbral (threshold_mode):
- "high_recall" -> 0.32
- "balanced"    -> 0.50
- "high_precision" -> 0.60
- "target_precision:<float>" -> calcula umbral en VALID para alcanzar esa precisión
- float -> umbral personalizado

Provee retrain_from_csv(file, activate=False, threshold_mode="high_recall").
"""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, Union

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
)
from sklearn.model_selection import train_test_split
from joblib import dump


# Rutas de artefactos
BASE: Path = Path(__file__).resolve().parent
# Save artifacts in repository-level models_store
STORE: Path = BASE.parent / "models_store"
VERSIONS: Path = STORE / "versions"
CURRENT: Path = STORE / "current"


# Columnas base esperadas (11 KOI)
BASE_FEATURES: List[str] = [
    "koi_period",
    "koi_duration",
    "koi_depth",
    "koi_steff",
    "koi_kepmag",
    "koi_prad",
    "koi_slogg",
    "koi_srad",
    "koi_teq",
    "koi_model_snr",
    "koi_impact",
]

# Derivadas usadas en predictor
DERIVED_FEATURES: List[str] = [
    "duty_cycle",
    "depth_frac",
    "rprstar_est",
    "log_period",
    "log_depth",
]


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _derive_features(df: pd.DataFrame) -> pd.DataFrame:
    if {"koi_period", "koi_duration", "koi_depth"}.issubset(df.columns):
        with np.errstate(divide="ignore", invalid="ignore"):
            df["duty_cycle"] = df["koi_duration"] / (df["koi_period"] * 24.0)
        df["depth_frac"] = (df["koi_depth"].clip(lower=1e-9)) * 1e-6
        df["rprstar_est"] = np.sqrt(df["depth_frac"])
    if "koi_period" in df:
        df["log_period"] = np.log10(df["koi_period"].clip(lower=1e-9))
    if "koi_depth" in df:
        df["log_depth"] = np.log10(df["koi_depth"].clip(lower=1e-9))
    return df


def _prepare_training_frame(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    df = _derive_features(_coerce_numeric(df.copy()))
    ordered: List[str] = [c for c in BASE_FEATURES + DERIVED_FEATURES if c in df.columns]
    missing = [c for c in BASE_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas para entrenamiento: {missing}")
    X = df[ordered].copy()
    # imputación simple
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median(numeric_only=True))
    return X, ordered


def train_val_test_split_frame(
    df: pd.DataFrame, label_col: str = "label_true", seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df, df, df
    stratify = None
    if label_col in df.columns:
        y = df[label_col].astype(int)
        # Si todas las clases existen, estratificar
        if y.nunique() == 2:
            stratify = y
    train_df, remain_df = train_test_split(
        df, test_size=0.4, random_state=seed, stratify=stratify
    )
    stratify_remain = None
    if label_col in remain_df.columns:
        y_rem = remain_df[label_col].astype(int)
        if y_rem.nunique() == 2:
            stratify_remain = y_rem
    val_df, test_df = train_test_split(
        remain_df, test_size=0.5, random_state=seed, stratify=stratify_remain
    )
    return train_df, val_df, test_df


def _compute_metrics(y_true: np.ndarray, proba: np.ndarray, y_hat: Optional[np.ndarray] = None) -> Dict[str, Any]:
    if y_hat is None:
        y_hat = (proba >= 0.5).astype(int)
    return dict(
        ROC_AUC=float(roc_auc_score(y_true, proba)) if len(np.unique(y_true)) > 1 else float("nan"),
        PR_AUC=float(average_precision_score(y_true, proba)) if len(np.unique(y_true)) > 1 else float("nan"),
        Accuracy=float(accuracy_score(y_true, y_hat)),
        Precision=float(precision_score(y_true, y_hat, zero_division=0)),
        Recall=float(recall_score(y_true, y_hat, zero_division=0)),
        F1=float(f1_score(y_true, y_hat, zero_division=0)),
        MCC=float(matthews_corrcoef(y_true, y_hat)) if len(np.unique(y_true)) > 1 else float("nan"),
    )


def _threshold_from_mode(
    mode: Union[str, float], y_true_valid: Optional[np.ndarray], proba_valid: Optional[np.ndarray]
) -> float:
    if isinstance(mode, (int, float)):
        return float(mode)
    if mode is None:
        return 0.32
    m = str(mode).strip().lower()
    if m == "high_recall":
        return 0.32
    if m == "balanced":
        return 0.50
    if m == "high_precision":
        return 0.60
    if m.startswith("target_precision"):
        # target_precision or target_precision:0.90
        target = 0.90
        parts = m.split(":", 1)
        if len(parts) == 2:
            try:
                target = float(parts[1])
            except ValueError:
                pass
        if y_true_valid is None or proba_valid is None:
            raise ValueError("Se requiere y_true y proba en VALID para target_precision.")
        prec, rec, thr = precision_recall_curve(y_true_valid, proba_valid)
        mask = prec[:-1] >= target
        if mask.any():
            idx = (rec[:-1][mask]).argmax()
            return float(thr[:-1][mask][idx])
        return float(thr[:-1][prec[:-1].argmax()])
    raise ValueError(
        "threshold_mode inválido. Use high_recall, balanced, high_precision, target_precision[:x] o float."
    )


@dataclass
class TrainResult:
    version_dir: Path
    model_path: Path
    config_path: Path
    threshold: float
    features: List[str]
    metrics_valid: Optional[Dict[str, Any]]
    metrics_test: Optional[Dict[str, Any]]


def _ensure_dirs() -> None:
    VERSIONS.mkdir(parents=True, exist_ok=True)
    CURRENT.mkdir(parents=True, exist_ok=True)


def _save_artifacts(version_dir: Path, model, features: List[str], threshold: float, extra: Optional[Dict[str, Any]] = None) -> Tuple[Path, Path]:
    version_dir.mkdir(parents=True, exist_ok=True)
    model_path = version_dir / "rf_koi.joblib"
    config_path = version_dir / "final_config.json"
    dump(model, model_path)
    cfg: Dict[str, Any] = {"features": features, "threshold": float(threshold)}
    if extra:
        cfg.update(extra)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return model_path, config_path


def _activate_version(version_dir: Path) -> None:
    CURRENT.mkdir(parents=True, exist_ok=True)
    # Copiar artefactos principales
    for name in ["rf_koi.joblib", "final_config.json"]:
        src = version_dir / name
        if src.exists():
            shutil.copy2(src, CURRENT / name)


def retrain_from_csv(
    file: Union[str, Path],
    activate: bool = False,
    threshold_mode: Union[str, float] = "high_recall",
    label_col: str = "label_true",
) -> TrainResult:
    """
    Reentrena modelo desde un CSV/JSON y guarda versión.

    file: ruta a CSV o JSON (registros). Debe contener label_true para métricas.
    activate: si True, copia artefactos a models_store/current.
    threshold_mode: ver descripción del módulo.
    """
    _ensure_dirs()
    file = Path(file)
    if not file.exists():
        raise FileNotFoundError(str(file))

    # Carga de datos
    if file.suffix.lower() == ".json":
        df = pd.read_json(file)
    else:
        df = pd.read_csv(file)

    if label_col not in df.columns:
        # Si no hay label, no se puede entrenar supervisado: devolver error claro
        raise ValueError("El archivo debe incluir columna 'label_true' para entrenamiento.")

    # Split
    train_df, val_df, test_df = train_val_test_split_frame(df, label_col=label_col, seed=42)

    # Preparación de features
    X_train, features = _prepare_training_frame(train_df)
    y_train = train_df[label_col].astype(int).values
    X_val, _ = _prepare_training_frame(val_df)
    y_val = val_df[label_col].astype(int).values
    X_test, _ = _prepare_training_frame(test_df)
    y_test = test_df[label_col].astype(int).values

    # Modelo
    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=12,
        min_samples_leaf=5,
        max_features="sqrt",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    proba_val = model.predict_proba(X_val)[:, 1]
    proba_test = model.predict_proba(X_test)[:, 1]

    # Umbral según modo (calculado en VALID cuando aplica)
    thr = _threshold_from_mode(threshold_mode, y_val, proba_val)

    yhat_val = (proba_val >= thr).astype(int)
    yhat_test = (proba_test >= thr).astype(int)

    metrics_valid = _compute_metrics(y_val, proba_val, yhat_val)
    metrics_test = _compute_metrics(y_test, proba_test, yhat_test)

    # Versionado
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    version_dir = VERSIONS / ts
    model_path, config_path = _save_artifacts(
        version_dir,
        model,
        features,
        thr,
        extra={
            "created_utc": ts,
            "base_features": BASE_FEATURES,
            "derived_features": DERIVED_FEATURES,
            "label_col": label_col,
            "metrics_valid": metrics_valid,
            "metrics_test": metrics_test,
        },
    )

    if activate:
        _activate_version(version_dir)

    return TrainResult(
        version_dir=version_dir,
        model_path=model_path,
        config_path=config_path,
        threshold=float(thr),
        features=features,
        metrics_valid=metrics_valid,
        metrics_test=metrics_test,
    )