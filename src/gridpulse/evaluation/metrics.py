"""Model evaluation metrics, calibration diagnostics, and subgroup error analysis."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def compute_binary_classification_metrics(
    y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5
) -> Dict[str, Any]:
    """Compute comprehensive binary classification and probability calibration metrics."""
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)
    if y_true_arr.size == 0 or y_prob_arr.size == 0:
        raise ValueError("Cannot compute metrics on empty arrays.")
    if y_true_arr.shape[0] != y_prob_arr.shape[0]:
        raise ValueError("y_true and y_prob must have identical length.")

    y_pred = (y_prob_arr >= threshold).astype(int)

    # Handle edge cases in tiny synthetic unit tests where only 1 class is present
    has_both_classes = len(np.unique(y_true_arr)) > 1
    roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr)) if has_both_classes else 0.5
    pr_auc = (
        float(average_precision_score(y_true_arr, y_prob_arr))
        if has_both_classes
        else float(np.mean(y_true_arr))
    )
    brier = float(brier_score_loss(y_true_arr, y_prob_arr))
    f1 = float(f1_score(y_true_arr, y_pred, zero_division=0))
    prec = float(precision_score(y_true_arr, y_pred, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred, zero_division=0))

    cm = confusion_matrix(y_true_arr, y_pred, labels=[0, 1])
    tn, fp, fn, tp = (int(x) for x in cm.ravel())

    return {
        "n_samples": int(y_true_arr.shape[0]),
        "positive_rate": round(float(np.mean(y_true_arr)), 4),
        "threshold": round(float(threshold), 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "brier_score": round(brier, 4),
        "f1_score": round(f1, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def compute_calibration_table(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> List[Dict[str, float]]:
    """Compute reliability / calibration curve bins."""
    prob_true, prob_pred = calibration_curve(
        y_true, y_prob, n_bins=n_bins, strategy="uniform"
    )
    return [
        {
            "bin_index": int(i + 1),
            "mean_predicted_prob": round(float(pp), 4),
            "observed_positive_fraction": round(float(pt), 4),
        }
        for i, (pp, pt) in enumerate(zip(prob_pred, prob_true))
    ]
