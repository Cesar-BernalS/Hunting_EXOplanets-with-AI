import numpy as np, pandas as pd
from typing import Optional, Dict, Any
from sklearn.metrics import (roc_auc_score, average_precision_score, accuracy_score,
                             precision_score, recall_score, f1_score, matthews_corrcoef,
                             confusion_matrix, precision_recall_curve)
from .predictor import predict_batch, THRESHOLD

def find_threshold_for_precision(y_true, proba, target_prec: float=0.90) -> float:
    prec, rec, thr = precision_recall_curve(y_true, proba)
    mask = prec[:-1] >= target_prec
    if mask.any():
        idx = (rec[:-1][mask]).argmax()
        return float(thr[:-1][mask][idx])
    return float(thr[:-1][prec[:-1].argmax()])

def summarize_for_app(df_inputs: pd.DataFrame,
                      meta_cols: list[str] | None = None,
                      label_true_col: Optional[str] = None,
                      threshold: float | None = None,
                      top_n: int = 10) -> Dict[str, Any]:
    meta_cols = meta_cols or []
    pred = predict_batch(df_inputs, threshold=threshold)
    df = df_inputs.copy()
    df["probability"], df["label"] = pred["probability"].values, pred["label"].values
    df["verdict"] = np.where(df["label"]==1, "Planet(1)", "FP(0)")

    cols_show = [c for c in meta_cols if c in df.columns] + \
                [c for c in ["probability","verdict","koi_period","koi_duration","koi_depth",
                             "koi_model_snr","duty_cycle","koi_prad","koi_impact"] if c in df.columns]

    top_pos = df.sort_values("probability", ascending=False).head(top_n)[cols_show]
    top_neg = df.sort_values("probability", ascending=True ).head(top_n)[cols_show]

    metrics = cm = fp = fn = None
    if label_true_col and label_true_col in df.columns:
        y_true, y_hat = df[label_true_col].astype(int).values, df["label"].values
        metrics = dict(
            ROC_AUC=float(roc_auc_score(y_true, df["probability"])),
            PR_AUC=float(average_precision_score(y_true, df["probability"])),
            Accuracy=float(accuracy_score(y_true, y_hat)),
            Precision=float(precision_score(y_true, y_hat)),
            Recall=float(recall_score(y_true, y_hat)),
            F1=float(f1_score(y_true, y_hat)),
            MCC=float(matthews_corrcoef(y_true, y_hat)),
        )
        cm = confusion_matrix(y_true, y_hat).tolist()
        fp = df[(y_hat==1) & (y_true==0)].sort_values("probability", ascending=False).head(top_n)[cols_show]
        fn = df[(y_hat==0) & (y_true==1)].sort_values("probability", ascending=True ).head(top_n)[cols_show]

    hist_counts, hist_edges = np.histogram(df["probability"].values, bins=30, range=(0,1))

    return {
        "threshold": float(THRESHOLD if threshold is None else threshold),
        "top_pos": top_pos, "top_neg": top_neg,
        "false_pos": fp, "false_neg": fn,
        "metrics": metrics, "confusion_matrix": cm,
        "hist_counts": hist_counts.tolist(), "hist_edges": hist_edges.tolist(),
        "verdict_counts": df["verdict"].value_counts().to_dict()
    }
