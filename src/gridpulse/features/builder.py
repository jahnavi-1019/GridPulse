"""Feature engineering for county-outage episodes and regional reliability profiles."""

from __future__ import annotations

import logging
import math
from typing import Dict, Optional

import polars as pl

from gridpulse.config import GridPulseConfig, STATE_METADATA, VTEC_PHENOM_LABELS
from gridpulse.utils.spark_session import save_parquet_atomic

logger = logging.getLogger(__name__)


def build_event_feature_table(
    hourly_df: pl.DataFrame,
    high_severity_threshold: float = 100.0,
    major_severity_threshold: float = 500.0,
) -> pl.DataFrame:
    """Aggregate hourly warning-matched rows to the county-outage episode level (fips_code, new_event_no)
    and engineer strictly causal (past-only) lag features for predictive modeling.
    """
    if hourly_df.height == 0:
        raise ValueError("Cannot build event features from an empty hourly DataFrame.")

    # Ensure chronological sort by fips_code and timestamp_utc
    sorted_hourly = hourly_df.sort(["fips_code", "timestamp_utc"])

    # Aggregate to unique (fips_code, new_event_no)
    events = (
        sorted_hourly.group_by(["fips_code", "new_event_no"], maintain_order=True)
        .agg(
            [
                pl.col("state").first().alias("state"),
                pl.col("county").first().alias("county"),
                pl.col("WFO").first().alias("WFO"),
                pl.col("timestamp_utc").min().alias("event_start_utc"),
                pl.col("timestamp_utc").max().alias("event_end_utc"),
                pl.col("year").first().alias("year"),
                pl.col("month").first().alias("month"),
                pl.col("hour_of_day").first().alias("onset_hour_utc"),
                pl.col("day_of_week").first().alias("onset_day_of_week"),
                pl.col("season").first().alias("season"),
                pl.len().alias("observed_matched_hours"),
                pl.col("evDur_Hr").first().alias("evDur_Hr"),
                pl.col("evDur_day").first().alias("evDur_day"),
                pl.col("Max_outage").first().alias("Max_outage"),
                pl.col("max_rolling_avg").first().alias("initial_outage_hr1"),
                pl.col("max_rolling_avg").max().alias("peak_matched_rolling_avg"),
                pl.col("max_rolling_avg").sum().alias("cumulative_customer_hours_proxy"),
                pl.col("median_sum").first().alias("county_baseline_median_sum"),
                pl.col("source_completeness_pct").first().alias("initial_completeness_pct"),
                pl.col("event_mean_completeness_pct").first().alias("event_mean_completeness_pct"),
                pl.col("event_min_completeness_pct").first().alias("event_min_completeness_pct"),
                pl.col("Matched_Count").first().alias("initial_matched_count"),
                pl.col("Matched_Count").max().alias("max_matched_count"),
                pl.col("primary_phenom").first().alias("primary_phenom"),
                pl.col("Matched_Events").first().alias("initial_matched_events"),
            ]
        )
        .sort(["fips_code", "event_start_utc", "new_event_no"])
    )

    # Engineer strictly causal historical features per county using shift(1) BEFORE rolling/cumulative ops
    events = events.with_columns(
        [
            (pl.col("Max_outage") >= high_severity_threshold)
            .cast(pl.Int32)
            .alias("target_high_severity_100"),
            (pl.col("Max_outage") >= major_severity_threshold)
            .cast(pl.Int32)
            .alias("target_major_severity_500"),
            (pl.col("Max_outage") / pl.col("county_baseline_median_sum")).alias(
                "normalized_peak_severity_ratio"
            ),
            (pl.col("initial_outage_hr1") / pl.col("county_baseline_median_sum")).alias(
                "initial_to_baseline_ratio"
            ),
            (pl.col("initial_matched_count") > 1)
            .cast(pl.Int32)
            .alias("initial_is_multi_hazard"),
            (pl.col("onset_hour_utc") * (2.0 * math.pi / 24.0)).sin().alias("sin_onset_hour"),
            (pl.col("onset_hour_utc") * (2.0 * math.pi / 24.0)).cos().alias("cos_onset_hour"),
            (pl.col("month") * (2.0 * math.pi / 12.0)).sin().alias("sin_month"),
            (pl.col("month") * (2.0 * math.pi / 12.0)).cos().alias("cos_month"),
        ]
    )

    # Strictly causal historical lags within each fips_code (uses only prior events k < i)
    events = events.with_columns(
        [
            pl.int_range(0, pl.len()).over("fips_code").alias("county_prior_event_count"),
            pl.col("Max_outage")
            .shift(1)
            .over("fips_code")
            .fill_null(pl.col("county_baseline_median_sum"))
            .alias("prior_1_max_outage"),
            pl.col("Max_outage")
            .shift(1)
            .rolling_mean(window_size=5, min_samples=1)
            .over("fips_code")
            .fill_null(pl.col("county_baseline_median_sum"))
            .alias("prior_5_mean_max_outage"),
            pl.col("evDur_Hr")
            .shift(1)
            .rolling_mean(window_size=5, min_samples=1)
            .over("fips_code")
            .fill_null(4.0)
            .alias("prior_5_mean_duration_hr"),
            pl.col("target_high_severity_100")
            .cast(pl.Float64)
            .shift(1)
            .rolling_mean(window_size=10, min_samples=1)
            .over("fips_code")
            .fill_null(0.12)
            .alias("prior_10_high_sev_rate"),
            (
                (
                    pl.col("event_start_utc")
                    - pl.col("event_start_utc").shift(1).over("fips_code")
                ).dt.total_hours()
            )
            .fill_null(720.0)
            .clip(lower_bound=0.0, upper_bound=8760.0)
            .alias("hours_since_prior_event"),
        ]
    )

    return events


def build_county_reliability_profiles(events_df: pl.DataFrame) -> pl.DataFrame:
    """Create county-level reliability and vulnerability profiles with explicit denominator & coverage context."""
    profiles = (
        events_df.group_by(["fips_code", "state", "county", "WFO"])
        .agg(
            [
                pl.len().alias("total_outage_events"),
                pl.col("observed_matched_hours").sum().alias("total_warning_matched_hours"),
                pl.col("evDur_Hr").sum().alias("total_event_duration_hours"),
                pl.col("evDur_Hr").median().round(2).alias("median_duration_hr"),
                pl.col("evDur_Hr").mean().round(2).alias("mean_duration_hr"),
                pl.col("evDur_Hr").quantile(0.90).round(2).alias("p90_duration_hr"),
                pl.col("Max_outage").median().round(2).alias("median_max_outage"),
                pl.col("Max_outage").mean().round(2).alias("mean_max_outage"),
                pl.col("Max_outage").quantile(0.90).round(2).alias("p90_max_outage"),
                pl.col("Max_outage").max().round(2).alias("peak_max_outage"),
                pl.col("cumulative_customer_hours_proxy")
                .sum()
                .round(2)
                .alias("total_customer_hours_proxy"),
                pl.col("county_baseline_median_sum")
                .first()
                .round(4)
                .alias("county_baseline_median_sum"),
                pl.col("normalized_peak_severity_ratio")
                .median()
                .round(3)
                .alias("median_normalized_severity_ratio"),
                pl.col("normalized_peak_severity_ratio")
                .mean()
                .round(3)
                .alias("mean_normalized_severity_ratio"),
                pl.col("normalized_peak_severity_ratio")
                .quantile(0.90)
                .round(3)
                .alias("p90_normalized_severity_ratio"),
                pl.col("target_high_severity_100")
                .sum()
                .alias("high_severity_events_ge100"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("high_severity_event_share_pct"),
                pl.col("target_major_severity_500")
                .sum()
                .alias("major_severity_events_ge500"),
                pl.col("event_mean_completeness_pct")
                .mean()
                .round(2)
                .alias("mean_event_completeness_pct"),
                pl.col("event_min_completeness_pct")
                .mean()
                .round(2)
                .alias("mean_event_min_completeness_pct"),
                (
                    (pl.col("event_mean_completeness_pct") >= 75.0)
                    .cast(pl.Float64)
                    .mean()
                    * 100.0
                )
                .round(2)
                .alias("high_coverage_event_share_pct"),
                pl.col("year").n_unique().alias("years_observed"),
                pl.col("primary_phenom").mode().first().alias("dominant_weather_phenom"),
            ]
        )
        .with_columns(
            [
                (pl.col("total_outage_events") / pl.col("years_observed").clip(lower_bound=1))
                .round(2)
                .alias("events_per_observed_year"),
                (
                    pl.col("total_customer_hours_proxy")
                    / pl.col("county_baseline_median_sum")
                )
                .round(2)
                .alias("baseline_normalized_cumulative_burden"),
                pl.when(pl.col("mean_event_completeness_pct") >= 75.0)
                .then(pl.lit("High Coverage (>=75%)"))
                .when(pl.col("mean_event_completeness_pct") >= 50.0)
                .then(pl.lit("Moderate Coverage (50-74%)"))
                .otherwise(pl.lit("Low Coverage (<50%)"))
                .alias("coverage_confidence_tier"),
            ]
        )
        .sort("total_outage_events", descending=True)
    )
    return profiles


def build_state_reliability_profiles(
    events_df: pl.DataFrame, county_profiles_df: pl.DataFrame
) -> pl.DataFrame:
    """Create state-level reliability summaries enriched with USPS codes and geographic coordinates."""
    state_df = (
        events_df.group_by("state")
        .agg(
            [
                pl.col("fips_code").n_unique().alias("observed_counties"),
                pl.len().alias("total_outage_events"),
                pl.col("observed_matched_hours").sum().alias("total_warning_matched_hours"),
                pl.col("evDur_Hr").median().round(2).alias("median_duration_hr"),
                pl.col("evDur_Hr").mean().round(2).alias("mean_duration_hr"),
                pl.col("Max_outage").median().round(2).alias("median_max_outage"),
                pl.col("Max_outage").mean().round(2).alias("mean_max_outage"),
                pl.col("Max_outage").quantile(0.90).round(2).alias("p90_max_outage"),
                pl.col("Max_outage").max().round(2).alias("peak_max_outage"),
                pl.col("cumulative_customer_hours_proxy")
                .sum()
                .round(2)
                .alias("total_customer_hours_proxy"),
                pl.col("normalized_peak_severity_ratio")
                .median()
                .round(3)
                .alias("median_normalized_severity_ratio"),
                pl.col("normalized_peak_severity_ratio")
                .quantile(0.90)
                .round(3)
                .alias("p90_normalized_severity_ratio"),
                pl.col("target_high_severity_100").sum().alias("high_severity_events_ge100"),
                (pl.col("target_high_severity_100").mean() * 100.0)
                .round(2)
                .alias("high_severity_event_share_pct"),
                pl.col("event_mean_completeness_pct")
                .mean()
                .round(2)
                .alias("mean_event_completeness_pct"),
                pl.col("primary_phenom").mode().first().alias("dominant_weather_phenom"),
            ]
        )
        .with_columns(
            (pl.col("total_outage_events") / pl.col("observed_counties"))
            .round(2)
            .alias("events_per_county")
        )
    )

    # Map state metadata (USPS code, lat, lon)
    abbr_map = {k: str(v["abbr"]) for k, v in STATE_METADATA.items()}
    lat_map = {k: float(v["lat"]) for k, v in STATE_METADATA.items()}
    lon_map = {k: float(v["lon"]) for k, v in STATE_METADATA.items()}

    state_df = state_df.with_columns(
        [
            pl.col("state").replace(abbr_map).alias("state_abbr"),
            pl.col("state").replace_strict(lat_map, default=39.5).alias("lat"),
            pl.col("state").replace_strict(lon_map, default=-98.35).alias("lon"),
        ]
    ).sort("total_outage_events", descending=True)

    return state_df


def run_feature_engineering_stage(
    config: Optional[GridPulseConfig] = None,
) -> Dict[str, str]:
    """Run Stage 3: Build event features, county reliability profiles, and state profiles."""
    cfg = config or GridPulseConfig()
    hourly_path = cfg.processed_dir / "eagle_vtec_hourly_clean.parquet"
    if not hourly_path.exists():
        raise FileNotFoundError(
            f"Processed hourly Parquet not found at {hourly_path}. Run preprocessing first."
        )

    hourly_df = pl.read_parquet(hourly_path)
    events_df = build_event_feature_table(
        hourly_df,
        high_severity_threshold=cfg.high_severity_threshold,
        major_severity_threshold=cfg.major_severity_threshold,
    )
    county_profiles = build_county_reliability_profiles(events_df)
    state_profiles = build_state_reliability_profiles(events_df, county_profiles)

    ev_path = save_parquet_atomic(
        events_df, cfg.features_dir / "event_features.parquet"
    )
    cnty_path = save_parquet_atomic(
        county_profiles, cfg.features_dir / "county_reliability_profiles.parquet"
    )
    st_path = save_parquet_atomic(
        state_profiles, cfg.features_dir / "state_reliability_profiles.parquet"
    )

    return {
        "event_features": str(ev_path),
        "county_reliability_profiles": str(cnty_path),
        "state_reliability_profiles": str(st_path),
    }
