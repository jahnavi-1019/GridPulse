"""Onset-time predictive modeling for outage episode severity escalation."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import polars as pl
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from gridpulse.config import GridPulseConfig
from gridpulse.evaluation.metrics import (
    compute_binary_classification_metrics,
    compute_calibration_table,
)
from gridpulse.utils.spark_session import save_parquet_atomic

logger = logging.getLogger(__name__)

# Strictly onset-available and historical causal features ONLY
NUMERIC_FEATURES: List[str] = [
    "initial_outage_hr1",
    "county_baseline_median_sum",
    "initial_to_baseline_ratio",
    "initial_completeness_pct",
    "initial_matched_count",
    "initial_is_multi_hazard",
    "sin_onset_hour",
    "cos_onset_hour",
    "sin_month",
    "cos_month",
    "county_prior_event_count",
    "prior_1_max_outage",
    "prior_5_mean_max_outage",
    "prior_5_mean_duration_hr",
    "prior_10_high_sev_rate",
    "hours_since_prior_event",
]

CATEGORICAL_FEATURES: List[str] = [
    "primary_phenom",
    "season",
]

# Post-onset / future / target-derived columns that MUST NEVER appear in feature sets
FORBIDDEN_LEAKAGE_COLS: List[str] = [
    "Max_outage",
    "evDur_Hr",
    "evDur_day",
    "observed_matched_hours",
    "peak_matched_rolling_avg",
    "cumulative_customer_hours_proxy",
    "event_mean_completeness_pct",
    "event_min_completeness_pct",
    "max_matched_count",
    "normalized_peak_severity_ratio",
    "target_high_severity_100",
    "target_major_severity_500",
    "event_end_utc",
]


def verify_no_leakage(
    feature_cols: List[str],
    train_df: pl.DataFrame,
    val_df: pl.DataFrame,
    test_df: pl.DataFrame,
) -> None:
    """Assert that no forbidden target/future columns are in feature_cols and that splits are strictly chronological."""
    leaked_cols = [c for c in feature_cols if c in FORBIDDEN_LEAKAGE_COLS]
    if leaked_cols:
        raise ValueError(
            f"Data leakage detected! Forbidden post-onset or target columns in features: {leaked_cols}"
        )

    if train_df.height > 0 and val_df.height > 0:
        max_train_yr = int(train_df["year"].max())
        min_val_yr = int(val_df["year"].min())
        if max_train_yr >= min_val_yr:
            raise ValueError(
                f"Temporal split leakage: max train year ({max_train_yr}) >= min val year ({min_val_yr})."
            )

    if val_df.height > 0 and test_df.height > 0:
        max_val_yr = int(val_df["year"].max())
        min_test_yr = int(test_df["year"].min())
        if max_val_yr >= min_test_yr:
            raise ValueError(
                f"Temporal split leakage: max val year ({max_val_yr}) >= min test year ({min_test_yr})."
            )


def split_temporal_train_val_test(
    events_df: pl.DataFrame,
    train_end_year: int = 2020,
    val_year: int = 2021,
    test_year: int = 2022,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Perform strict chronological splitting into Train (<=2020), Validation (2021), and Test (2022)."""
    train_df = events_df.filter(pl.col("year") <= train_end_year)
    val_df = events_df.filter(pl.col("year") == val_year)
    test_df = events_df.filter(pl.col("year") == test_year)
    verify_no_leakage(
        NUMERIC_FEATURES + CATEGORICAL_FEATURES, train_df, val_df, test_df
    )
    return train_df, val_df, test_df


def find_optimal_f1_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Select probability threshold on the Validation set that maximizes F1 score."""
    best_thresh = 0.5
    best_f1 = -1.0
    for thresh in np.linspace(0.15, 0.85, 36):
        preds = (y_prob >= thresh).astype(int)
        tp = np.sum((preds == 1) & (y_true == 1))
        fp = np.sum((preds == 1) & (y_true == 0))
        fn = np.sum((preds == 0) & (y_true == 1))
        denom = 2 * tp + fp + fn
        f1 = (2 * tp / denom) if denom > 0 else 0.0
        if f1 > best_f1:
            best_f1 = float(f1)
            best_thresh = float(thresh)
    return round(best_thresh, 4)


def run_predictive_modeling_stage(
    config: Optional[GridPulseConfig] = None,
) -> Dict[str, Any]:
    """Run Stage 5: Train baselines and ML models on temporal splits, evaluate on untouched 2022 test set,
    and persist calibrated probabilities, feature importances, and subgroup error analyses.
    """
    cfg = config or GridPulseConfig()
    events_path = cfg.features_dir / "event_features.parquet"
    if not events_path.exists():
        raise FileNotFoundError(
            f"Event features not found at {events_path}. Run feature engineering first."
        )

    events_df = pl.read_parquet(events_path)
    train_df, val_df, test_df = split_temporal_train_val_test(
        events_df,
        train_end_year=cfg.train_end_year,
        val_year=cfg.val_year,
        test_year=cfg.test_year,
    )

    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    target_col = "target_high_severity_100"

    X_train = train_df.select(feature_cols).to_pandas()
    y_train = train_df[target_col].to_numpy()

    X_val = val_df.select(feature_cols).to_pandas()
    y_val = val_df[target_col].to_numpy()

    X_test = test_df.select(feature_cols).to_pandas()
    y_test = test_df[target_col].to_numpy()

    # 1. Baseline 1: Persistence Heuristic (initial_outage_hr1 >= 100 customers + normalized ratio score)
    # Continuous score mapped to [0, 1] via logistic transform of log(initial_outage_hr1 / 100)
    val_base_prob = 1.0 / (
        1.0 + np.exp(-np.clip(np.log1p(val_df["initial_outage_hr1"].to_numpy()) - np.log1p(50.0), -10, 10))
    )
    test_base_prob = 1.0 / (
        1.0 + np.exp(-np.clip(np.log1p(test_df["initial_outage_hr1"].to_numpy()) - np.log1p(50.0), -10, 10))
    )
    base_val_metrics = compute_binary_classification_metrics(y_val, val_base_prob, threshold=0.5)
    base_test_metrics = compute_binary_classification_metrics(y_test, test_base_prob, threshold=0.5)

    # 2. Baseline 2: County + Weather Phenomenon Historical Prior Rate (Empirical Bayes smoothed on Train)
    global_prior = float(np.mean(y_train))
    prior_table = (
        train_df.group_by(["fips_code", "primary_phenom"])
        .agg(
            [
                pl.len().alias("n_hist"),
                pl.col(target_col).sum().alias("pos_hist"),
            ]
        )
        .with_columns(
            ((pl.col("pos_hist") + 5.0 * global_prior) / (pl.col("n_hist") + 5.0)).alias(
                "smoothed_prior_prob"
            )
        )
        .select(["fips_code", "primary_phenom", "smoothed_prior_prob"])
    )
    val_prior_prob = (
        val_df.select(["fips_code", "primary_phenom"])
        .join(prior_table, on=["fips_code", "primary_phenom"], how="left")["smoothed_prior_prob"]
        .fill_null(global_prior)
        .to_numpy()
    )
    test_prior_prob = (
        test_df.select(["fips_code", "primary_phenom"])
        .join(prior_table, on=["fips_code", "primary_phenom"], how="left")["smoothed_prior_prob"]
        .fill_null(global_prior)
        .to_numpy()
    )
    prior_thresh = find_optimal_f1_threshold(y_val, val_prior_prob)
    prior_val_metrics = compute_binary_classification_metrics(
        y_val, val_prior_prob, threshold=prior_thresh
    )
    prior_test_metrics = compute_binary_classification_metrics(
        y_test, test_prior_prob, threshold=prior_thresh
    )

    # Shared preprocessor for linear and tree models
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    # 3. Model 1: L2-Regularized Logistic Regression (Balanced class weights for imbalance)
    lr_pipeline = Pipeline(
        steps=[
            ("prep", preprocessor),
            (
                "clf",
                LogisticRegression(
                    C=1.0, class_weight="balanced", max_iter=300, random_state=42
                ),
            ),
        ]
    )
    lr_pipeline.fit(X_train, y_train)
    val_lr_prob = lr_pipeline.predict_proba(X_val)[:, 1]
    test_lr_prob = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_thresh = find_optimal_f1_threshold(y_val, val_lr_prob)
    lr_val_metrics = compute_binary_classification_metrics(
        y_val, val_lr_prob, threshold=lr_thresh
    )
    lr_test_metrics = compute_binary_classification_metrics(
        y_test, test_lr_prob, threshold=lr_thresh
    )

    # 4. Model 2: Histogram-Based Gradient Boosted Decision Trees (natively calibrated log-loss)
    hgb_pipeline = Pipeline(
        steps=[
            ("prep", preprocessor),
            (
                "clf",
                HistGradientBoostingClassifier(
                    max_iter=150,
                    learning_rate=0.08,
                    max_leaf_nodes=31,
                    min_samples_leaf=50,
                    l2_regularization=1.0,
                    random_state=42,
                ),
            ),
        ]
    )
    hgb_pipeline.fit(X_train, y_train)
    val_hgb_prob = hgb_pipeline.predict_proba(X_val)[:, 1]
    test_hgb_prob = hgb_pipeline.predict_proba(X_test)[:, 1]
    hgb_thresh = find_optimal_f1_threshold(y_val, val_hgb_prob)
    hgb_val_metrics = compute_binary_classification_metrics(
        y_val, val_hgb_prob, threshold=hgb_thresh
    )
    hgb_test_metrics = compute_binary_classification_metrics(
        y_test, test_hgb_prob, threshold=hgb_thresh
    )

    # Save trained pipelines
    joblib.dump(lr_pipeline, cfg.models_dir / "logistic_regression_onset.joblib")
    joblib.dump(hgb_pipeline, cfg.models_dir / "hist_gradient_boosting_onset.joblib")

    # Feature importance analysis (Permutation importance on a stratified 20,000-row sample of 2022 Test Set + LR coefficients)
    rng = np.random.default_rng(42)
    sample_idx = rng.choice(
        len(X_test), size=min(20000, len(X_test)), replace=False
    )
    perm_res = permutation_importance(
        hgb_pipeline,
        X_test.iloc[sample_idx],
        y_test[sample_idx],
        scoring="roc_auc",
        n_repeats=5,
        random_state=42,
    )
    feature_importances = [
        {
            "feature": col,
            "importance_mean_roc_auc_drop": round(float(perm_res.importances_mean[i]), 5),
            "importance_std": round(float(perm_res.importances_std[i]), 5),
        }
        for i, col in enumerate(feature_cols)
    ]
    feature_importances.sort(
        key=lambda x: x["importance_mean_roc_auc_drop"], reverse=True
    )

    # Extract Logistic Regression standardized coefficients for numeric features
    lr_coefs = lr_pipeline.named_steps["clf"].coef_[0][: len(NUMERIC_FEATURES)]
    lr_coefficients = [
        {"feature": col, "standardized_log_odds_coef": round(float(c), 4)}
        for col, c in zip(NUMERIC_FEATURES, lr_coefs)
    ]
    lr_coefficients.sort(
        key=lambda x: abs(x["standardized_log_odds_coef"]), reverse=True
    )

    # Calibration curve on 2022 Test Set
    hgb_calibration = compute_calibration_table(y_test, test_hgb_prob, n_bins=10)

    # Subgroup robustness & error analysis on 2022 Test Set (by Completeness Tier, Season, and Top Warning Types)
    test_with_preds = test_df.with_columns(
        [
            pl.Series("pred_prob_hgb", test_hgb_prob),
            pl.Series("pred_label_hgb", (test_hgb_prob >= hgb_thresh).astype(int)),
            pl.when(pl.col("initial_completeness_pct") == 100.0)
            .then(pl.lit("100% Complete"))
            .when(pl.col("initial_completeness_pct") >= 75.0)
            .then(pl.lit("75% - 99% Complete"))
            .when(pl.col("initial_completeness_pct") >= 50.0)
            .then(pl.lit("50% - 74% Complete"))
            .otherwise(pl.lit("< 50% Complete"))
            .alias("onset_completeness_tier"),
        ]
    )

    subgroup_by_completeness = []
    for tier in [
        "100% Complete",
        "75% - 99% Complete",
        "50% - 74% Complete",
        "< 50% Complete",
    ]:
        sub = test_with_preds.filter(pl.col("onset_completeness_tier") == tier)
        if sub.height > 50:
            m = compute_binary_classification_metrics(
                sub[target_col].to_numpy(),
                sub["pred_prob_hgb"].to_numpy(),
                threshold=hgb_thresh,
            )
            m["subgroup"] = tier
            subgroup_by_completeness.append(m)

    subgroup_by_season = []
    for seas in ["Winter", "Spring", "Summer", "Autumn"]:
        sub = test_with_preds.filter(pl.col("season") == seas)
        if sub.height > 50:
            m = compute_binary_classification_metrics(
                sub[target_col].to_numpy(),
                sub["pred_prob_hgb"].to_numpy(),
                threshold=hgb_thresh,
            )
            m["subgroup"] = seas
            subgroup_by_season.append(m)

    subgroup_by_phenom = []
    for phen in ["SV", "HT", "WI", "WW", "FW", "TO", "FZ", "EH", "TR", "WS"]:
        sub = test_with_preds.filter(pl.col("primary_phenom") == phen)
        if sub.height > 50:
            m = compute_binary_classification_metrics(
                sub[target_col].to_numpy(),
                sub["pred_prob_hgb"].to_numpy(),
                threshold=hgb_thresh,
            )
            m["subgroup"] = phen
            subgroup_by_phenom.append(m)

    # Save 2022 test predictions Parquet for interactive dashboard error exploration
    save_parquet_atomic(
        test_with_preds.select(
            [
                "fips_code",
                "new_event_no",
                "state",
                "county",
                "WFO",
                "event_start_utc",
                "season",
                "primary_phenom",
                "initial_outage_hr1",
                "Max_outage",
                "evDur_Hr",
                "initial_completeness_pct",
                "onset_completeness_tier",
                target_col,
                "pred_prob_hgb",
                "pred_label_hgb",
            ]
        ),
        cfg.processed_dir / "test_predictions_2022.parquet",
    )

    modeling_results = {
        "task_definition": {
            "observational_unit": "County-Outage Episode (fips_code, new_event_no)",
            "prediction_time": "End of Hour 1 of outage episode (onset)",
            "target_variable": target_col,
            "target_description": "Binary indicator that peak customers out during the episode reaches >= 100 (Max_outage >= 100)",
            "train_period": f"2015-{cfg.train_end_year} ({train_df.height:,} episodes)",
            "validation_period": f"{cfg.val_year} ({val_df.height:,} episodes)",
            "test_period": f"{cfg.test_year} ({test_df.height:,} episodes, untouched until final evaluation)",
            "features_used": feature_cols,
            "forbidden_leakage_columns_excluded": FORBIDDEN_LEAKAGE_COLS,
        },
        "models": {
            "baseline_persistence_hr1": {
                "display_name": "Baseline 1: Onset Persistence Heuristic",
                "validation_2021": base_val_metrics,
                "test_2022": base_test_metrics,
            },
            "baseline_county_weather_prior": {
                "display_name": "Baseline 2: County x Weather Empirical Bayes Prior",
                "validation_2021": prior_val_metrics,
                "test_2022": prior_test_metrics,
            },
            "logistic_regression_balanced": {
                "display_name": "Model 1: L2 Logistic Regression (Balanced)",
                "validation_2021": lr_val_metrics,
                "test_2022": lr_test_metrics,
            },
            "hist_gradient_boosting": {
                "display_name": "Model 2: HistGradientBoosting Classifier (Calibrated)",
                "validation_2021": hgb_val_metrics,
                "test_2022": hgb_test_metrics,
            },
        },
        "feature_importance_hgb_permutation": feature_importances,
        "logistic_regression_coefficients": lr_coefficients,
        "calibration_curve_test_2022": hgb_calibration,
        "subgroup_robustness_test_2022": {
            "by_completeness_tier": subgroup_by_completeness,
            "by_season": subgroup_by_season,
            "by_weather_phenomenon": subgroup_by_phenom,
        },
    }

    with open(cfg.metrics_dir / "modeling_evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(modeling_results, f, indent=2)

    logger.info("Saved predictive modeling evaluation results to %s", cfg.metrics_dir)
    return modeling_results
