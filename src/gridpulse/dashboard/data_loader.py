"""Cached data loading helpers for the GridPulse Streamlit dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import polars as pl
import streamlit as st

from gridpulse.config import GridPulseConfig


@st.cache_resource
def get_config() -> GridPulseConfig:
    return GridPulseConfig()


@st.cache_data(ttl=3600)
def load_json_metrics(filename: str) -> Dict[str, Any]:
    cfg = get_config()
    path = cfg.metrics_dir / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Metrics file '{filename}' not found at {path}. Run `python scripts/run_pipeline.py --stage all` first."
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=3600)
def load_parquet_pandas(subdir: str, filename: str) -> pd.DataFrame:
    cfg = get_config()
    base = cfg.processed_dir if subdir == "processed" else cfg.features_dir
    path = base / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Parquet file '{filename}' not found at {path}. Run `python scripts/run_pipeline.py --stage all` first."
        )
    return pl.read_parquet(path).to_pandas()


@st.cache_data(ttl=3600)
def load_filtered_event_summary(
    years: tuple[int, int],
    states: tuple[str, ...],
    phenoms: tuple[str, ...],
    min_completeness: float,
) -> Dict[str, Any]:
    """Query event_features.parquet lazily with Polars predicate pushdown so raw rows never bloat memory."""
    cfg = get_config()
    path = cfg.features_dir / "event_features.parquet"
    lf = pl.scan_parquet(path).filter(
        (pl.col("year") >= years[0])
        & (pl.col("year") <= years[1])
        & (pl.col("event_mean_completeness_pct") >= min_completeness)
    )
    if states:
        lf = lf.filter(pl.col("state").is_in(list(states)))
    if phenoms:
        lf = lf.filter(pl.col("primary_phenom").is_in(list(phenoms)))

    df = lf.collect()
    if df.height == 0:
        return {"empty": True, "n_events": 0}

    kpi = {
        "empty": False,
        "n_events": int(df.height),
        "n_counties": int(df["fips_code"].n_unique()),
        "n_states": int(df["state"].n_unique()),
        "median_max_outage": round(float(df["Max_outage"].median()), 2),
        "mean_max_outage": round(float(df["Max_outage"].mean()), 2),
        "p90_max_outage": round(float(df["Max_outage"].quantile(0.90)), 2),
        "median_duration_hr": round(float(df["evDur_Hr"].median()), 2),
        "mean_duration_hr": round(float(df["evDur_Hr"].mean()), 2),
        "high_sev_rate_pct": round(
            float(df["target_high_severity_100"].mean() * 100.0), 2
        ),
        "mean_completeness_pct": round(
            float(df["event_mean_completeness_pct"].mean()), 2
        ),
    }

    by_ym = (
        df.group_by(["year", "month"])
        .agg(
            [
                pl.len().alias("outage_events"),
                pl.col("Max_outage").median().round(2).alias("median_max_outage"),
                pl.col("Max_outage").quantile(0.90).round(2).alias("p90_max_outage"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("high_severity_rate_pct"),
                pl.col("event_mean_completeness_pct")
                .mean()
                .round(2)
                .alias("mean_completeness_pct"),
            ]
        )
        .sort(["year", "month"])
        .with_columns(
            (
                pl.col("year").cast(pl.String)
                + "-"
                + pl.col("month").cast(pl.String).str.pad_start(2, "0")
            ).alias("year_month")
        )
        .to_pandas()
    )

    by_hour = (
        df.group_by("onset_hour_utc")
        .agg(
            [
                pl.len().alias("outage_events"),
                pl.col("Max_outage").median().round(2).alias("median_max_outage"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("high_severity_rate_pct"),
            ]
        )
        .sort("onset_hour_utc")
        .to_pandas()
    )

    by_season = (
        df.group_by("season")
        .agg(
            [
                pl.len().alias("outage_events"),
                pl.col("Max_outage").median().round(2).alias("median_max_outage"),
                pl.col("evDur_Hr").mean().round(2).alias("mean_duration_hr"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("high_severity_rate_pct"),
            ]
        )
        .sort("outage_events", descending=True)
        .to_pandas()
    )

    by_phenom = (
        df.group_by("primary_phenom")
        .agg(
            [
                pl.len().alias("outage_events"),
                pl.col("Max_outage").median().round(2).alias("median_max_outage"),
                pl.col("Max_outage").mean().round(2).alias("mean_max_outage"),
                pl.col("Max_outage").quantile(0.90).round(2).alias("p90_max_outage"),
                pl.col("evDur_Hr").mean().round(2).alias("mean_duration_hr"),
                pl.col("normalized_peak_severity_ratio")
                .median()
                .round(3)
                .alias("median_norm_ratio"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("high_severity_rate_pct"),
                pl.col("event_mean_completeness_pct")
                .mean()
                .round(2)
                .alias("mean_completeness_pct"),
            ]
        )
        .sort("outage_events", descending=True)
        .to_pandas()
    )

    kpi["by_ym"] = by_ym
    kpi["by_hour"] = by_hour
    kpi["by_season"] = by_season
    kpi["by_phenom"] = by_phenom
    return kpi
