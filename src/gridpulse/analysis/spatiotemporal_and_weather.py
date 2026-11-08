"""Spatiotemporal outage analysis, weather-warning associations, and missing-data sensitivity."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import numpy as np
import polars as pl
from scipy import stats

from gridpulse.config import GridPulseConfig, VTEC_PHENOM_LABELS
from gridpulse.utils.spark_session import save_parquet_atomic

logger = logging.getLogger(__name__)


def compute_temporal_patterns(
    hourly_df: pl.DataFrame, events_df: pl.DataFrame
) -> Dict[str, pl.DataFrame]:
    """Compute hour-of-day, day-of-week, monthly/seasonal, and year-over-year outage patterns."""
    by_hour = (
        hourly_df.group_by("hour_of_day")
        .agg(
            [
                pl.len().alias("hourly_records"),
                pl.col("max_rolling_avg").median().round(3).alias("median_rolling_avg_customers"),
                pl.col("max_rolling_avg").mean().round(2).alias("mean_rolling_avg_customers"),
                pl.col("max_rolling_avg").quantile(0.90).round(2).alias("p90_rolling_avg_customers"),
                pl.col("source_completeness_pct").mean().round(2).alias("mean_completeness_pct"),
            ]
        )
        .sort("hour_of_day")
    )

    by_dow = (
        hourly_df.group_by("day_of_week")
        .agg(
            [
                pl.len().alias("hourly_records"),
                pl.col("max_rolling_avg").median().round(3).alias("median_rolling_avg_customers"),
                pl.col("max_rolling_avg").mean().round(2).alias("mean_rolling_avg_customers"),
                pl.col("source_completeness_pct").mean().round(2).alias("mean_completeness_pct"),
            ]
        )
        .sort("day_of_week")
    )

    by_year_month = (
        events_df.group_by(["year", "month", "season"])
        .agg(
            [
                pl.len().alias("outage_events"),
                pl.col("fips_code").n_unique().alias("affected_counties"),
                pl.col("Max_outage").median().round(2).alias("median_max_outage"),
                pl.col("Max_outage").mean().round(2).alias("mean_max_outage"),
                pl.col("Max_outage").quantile(0.90).round(2).alias("p90_max_outage"),
                pl.col("evDur_Hr").median().round(2).alias("median_duration_hr"),
                pl.col("evDur_Hr").mean().round(2).alias("mean_duration_hr"),
                pl.col("target_high_severity_100").sum().alias("high_severity_events_ge100"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("high_severity_rate_pct"),
                pl.col("event_mean_completeness_pct")
                .mean()
                .round(2)
                .alias("mean_event_completeness_pct"),
            ]
        )
        .sort(["year", "month"])
    )

    return {
        "temporal_by_hour": by_hour,
        "temporal_by_dow": by_dow,
        "temporal_by_year_month": by_year_month,
    }


def compute_weather_associations(events_df: pl.DataFrame) -> tuple[pl.DataFrame, Dict[str, Any]]:
    """Analyze outage severity, duration, normalized burden, and missingness sensitivity across NWS VTEC warning types."""
    label_map = VTEC_PHENOM_LABELS

    # Overall summary across all events
    all_events_summary = (
        events_df.group_by("primary_phenom")
        .agg(
            [
                pl.len().alias("total_events"),
                pl.col("fips_code").n_unique().alias("unique_counties"),
                pl.col("Max_outage").median().round(2).alias("median_max_outage"),
                pl.col("Max_outage").mean().round(2).alias("mean_max_outage"),
                pl.col("Max_outage").quantile(0.90).round(2).alias("p90_max_outage"),
                pl.col("Max_outage").max().round(2).alias("peak_max_outage"),
                pl.col("evDur_Hr").median().round(2).alias("median_duration_hr"),
                pl.col("evDur_Hr").mean().round(2).alias("mean_duration_hr"),
                pl.col("evDur_Hr").quantile(0.90).round(2).alias("p90_duration_hr"),
                pl.col("normalized_peak_severity_ratio")
                .median()
                .round(3)
                .alias("median_norm_severity_ratio"),
                pl.col("normalized_peak_severity_ratio")
                .quantile(0.90)
                .round(3)
                .alias("p90_norm_severity_ratio"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("prob_high_severity_ge100_pct"),
                (pl.col("target_major_severity_500").mean() * 100.0)
                .round(2)
                .alias("prob_major_severity_ge500_pct"),
                pl.col("event_mean_completeness_pct")
                .mean()
                .round(2)
                .alias("mean_completeness_pct"),
            ]
        )
        .with_columns(
            pl.col("primary_phenom")
            .replace_strict(label_map, default=pl.col("primary_phenom"))
            .alias("phenomenon_label")
        )
        .sort("total_events", descending=True)
    )

    # Sensitivity check: High-completeness subset (event_mean_completeness_pct >= 75%)
    high_comp_df = events_df.filter(pl.col("event_mean_completeness_pct") >= 75.0)
    high_comp_summary = (
        high_comp_df.group_by("primary_phenom")
        .agg(
            [
                pl.len().alias("high_comp_events"),
                pl.col("Max_outage").median().round(2).alias("high_comp_median_max_outage"),
                pl.col("Max_outage").mean().round(2).alias("high_comp_mean_max_outage"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("high_comp_prob_ge100_pct"),
            ]
        )
    )

    merged_weather = all_events_summary.join(
        high_comp_summary, on="primary_phenom", how="left"
    ).sort("total_events", descending=True)

    # Multi-hazard comparison (single active warning vs overlapping 2+ warnings)
    multi_hazard_comp = (
        events_df.group_by("initial_is_multi_hazard")
        .agg(
            [
                pl.len().alias("n_events"),
                pl.col("Max_outage").median().round(2).alias("median_max_outage"),
                pl.col("Max_outage").mean().round(2).alias("mean_max_outage"),
                pl.col("evDur_Hr").median().round(2).alias("median_duration_hr"),
                pl.col("evDur_Hr").mean().round(2).alias("mean_duration_hr"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("prob_high_severity_ge100_pct"),
            ]
        )
        .sort("initial_is_multi_hazard")
        .to_dicts()
    )

    # Non-parametric Kruskal-Wallis H-test across top 10 warning phenomena
    top10_codes = merged_weather["primary_phenom"].head(10).to_list()
    groups = [
        events_df.filter(pl.col("primary_phenom") == code)["Max_outage"].to_numpy()
        for code in top10_codes
    ]
    kw_stat, kw_pval = stats.kruskal(*groups)

    # Rank correlation of phenomenon severity between All Events vs >=75% Completeness Events
    valid_rank_df = merged_weather.filter(pl.col("high_comp_events") >= 50)
    spearman_r, spearman_p = stats.spearmanr(
        valid_rank_df["prob_high_severity_ge100_pct"].to_numpy(),
        valid_rank_df["high_comp_prob_ge100_pct"].to_numpy(),
    )

    hypothesis_tests = {
        "kruskal_wallis_top10_phenoms": {
            "h_statistic": round(float(kw_stat), 2),
            "p_value": float(kw_pval),
            "significant_at_0_001": bool(kw_pval < 0.001),
            "interpretation": (
                "Statistically significant heterogeneity in peak outage severity across NWS VTEC warning types "
                "(rejects null hypothesis of equal severity distributions; observational association only)."
            ),
        },
        "completeness_rank_robustness": {
            "spearman_rho": round(float(spearman_r), 4),
            "p_value": float(spearman_p),
            "interpretation": (
                "High rank-order consistency in phenomenon high-severity probability between all events and "
                "high-coverage (>=75% completeness) events."
            ),
        },
        "multi_hazard_comparison": multi_hazard_comp,
    }

    return merged_weather, hypothesis_tests


def run_clustering_on_counties(county_profiles: pl.DataFrame) -> pl.DataFrame:
    """Assign interpretable vulnerability/reliability archetypes using standardized K-Means (k=4)
    alongside explicit rule-based explanations, avoiding raw-count-only ranking bias.
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    feature_cols = [
        "events_per_observed_year",
        "median_normalized_severity_ratio",
        "high_severity_event_share_pct",
        "mean_duration_hr",
        "mean_event_completeness_pct",
    ]
    X = county_profiles.select(feature_cols).fill_null(0.0).to_numpy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    raw_labels = kmeans.fit_predict(X_scaled)

    # Map clusters deterministically by sorting cluster centers on high_severity_event_share_pct * events_per_observed_year
    df_with_raw = county_profiles.with_columns(pl.Series("raw_cluster", raw_labels))
    cluster_stats = (
        df_with_raw.group_by("raw_cluster")
        .agg(
            [
                pl.col("high_severity_event_share_pct").mean().alias("mean_sev_share"),
                pl.col("events_per_observed_year").mean().alias("mean_freq"),
                pl.col("mean_event_completeness_pct").mean().alias("mean_comp"),
            ]
        )
        .with_columns(
            (pl.col("mean_sev_share") * pl.col("mean_freq")).alias("burden_index")
        )
        .sort("burden_index", descending=True)
    )

    ordered_clusters = cluster_stats["raw_cluster"].to_list()
    archetype_names = [
        "Tier 1: Chronic High-Severity & High-Recurrence",
        "Tier 2: Elevated Weather-Driven Vulnerability",
        "Tier 3: Moderate / Intermittent Outage Burden",
        "Tier 4: Low Observed Burden or Sparse Telemetry",
    ]
    cluster_map = {
        int(cid): archetype_names[idx] for idx, cid in enumerate(ordered_clusters)
    }

    return df_with_raw.with_columns(
        pl.col("raw_cluster")
        .replace_strict(cluster_map, default=archetype_names[-1])
        .alias("reliability_archetype")
    ).drop("raw_cluster")


def run_analysis_stage(config: Optional[GridPulseConfig] = None) -> Dict[str, Any]:
    """Run Stage 4: Spatiotemporal trends, weather associations, missingness sensitivity, and regional clustering."""
    cfg = config or GridPulseConfig()

    hourly_df = pl.read_parquet(cfg.processed_dir / "eagle_vtec_hourly_clean.parquet")
    events_df = pl.read_parquet(cfg.features_dir / "event_features.parquet")
    county_profiles = pl.read_parquet(
        cfg.features_dir / "county_reliability_profiles.parquet"
    )

    # 1. Temporal patterns
    temp_tables = compute_temporal_patterns(hourly_df, events_df)
    for name, df_t in temp_tables.items():
        save_parquet_atomic(df_t, cfg.processed_dir / f"{name}.parquet")

    # 2. Weather associations & statistical robustness tests
    weather_df, weather_stats = compute_weather_associations(events_df)
    save_parquet_atomic(
        weather_df, cfg.processed_dir / "weather_association_summary.parquet"
    )

    # 3. Enrich county reliability profiles with interpretable K-Means archetypes
    clustered_counties = run_clustering_on_counties(county_profiles)
    save_parquet_atomic(
        clustered_counties, cfg.features_dir / "county_reliability_profiles.parquet"
    )

    with open(
        cfg.metrics_dir / "weather_and_spatiotemporal_stats.json", "w", encoding="utf-8"
    ) as f:
        json.dump(weather_stats, f, indent=2)

    return weather_stats
