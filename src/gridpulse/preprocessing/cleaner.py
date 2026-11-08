"""Data cleaning, timestamp parsing, deduplication, and Parquet materialization."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import polars as pl

from gridpulse.config import GridPulseConfig, VTEC_PHENOM_LABELS
from gridpulse.ingestion.schema_and_audit import (
    AVAILABILITY_REQUIRED_COLS,
    EAGLE_VTEC_REQUIRED_COLS,
    SENSITIVITY_REQUIRED_COLS,
    validate_required_columns,
)
from gridpulse.utils.spark_session import save_parquet_atomic

logger = logging.getLogger(__name__)


def clean_eagle_vtec_dataframe(df: pl.DataFrame) -> tuple[pl.DataFrame, Dict[str, int]]:
    """Clean, validate, deduplicate, and enrich the EAGLE-I VTEC hourly DataFrame."""
    validate_required_columns(df.columns, EAGLE_VTEC_REQUIRED_COLS, "Eagle_I_VTEC")
    initial_rows = df.height
    if initial_rows == 0:
        raise ValueError("Input EAGLE-I VTEC DataFrame is empty.")

    # Parse ISO-8601 UTC timestamp strictly
    df_parsed = df.with_columns(
        pl.col("Hour").str.to_datetime("%Y-%m-%dT%H:%M:%SZ", strict=False).alias("timestamp_utc")
    )
    invalid_ts_rows = int(df_parsed.filter(pl.col("timestamp_utc").is_null()).height)
    df_valid_ts = df_parsed.filter(pl.col("timestamp_utc").is_not_null())

    # Filter out any implausible or corrupted rows
    df_plausible = df_valid_ts.filter(
        (pl.col("fips_code") >= 1000)
        & (pl.col("fips_code") <= 99999)
        & (pl.col("max_rolling_avg") >= 0.0)
        & (pl.col("Max_outage") >= 0.0)
        & (pl.col("evDur_Hr") > 0)
        & (pl.col("source_completeness_pct") >= 0.0)
        & (pl.col("source_completeness_pct") <= 100.0)
        & (pl.col("Matched_Count") > 0)
    )
    implausible_rows_removed = int(df_valid_ts.height - df_plausible.height)

    # Deduplicate on (fips_code, Hour) keeping first after sorting
    df_dedup = df_plausible.sort(["fips_code", "timestamp_utc"]).unique(
        subset=["fips_code", "Hour"], keep="first", maintain_order=True
    )
    duplicate_rows_removed = int(df_plausible.height - df_dedup.height)

    # Enrich with temporal, completeness tier, and parsed warning attributes
    df_enriched = df_dedup.with_columns(
        [
            pl.col("timestamp_utc").dt.date().alias("date_utc"),
            pl.col("timestamp_utc").dt.year().cast(pl.Int32).alias("year"),
            pl.col("timestamp_utc").dt.month().cast(pl.Int32).alias("month"),
            pl.col("timestamp_utc").dt.hour().cast(pl.Int32).alias("hour_of_day"),
            pl.col("timestamp_utc").dt.weekday().cast(pl.Int32).alias("day_of_week"),
            pl.when(pl.col("timestamp_utc").dt.month().is_in([12, 1, 2]))
            .then(pl.lit("Winter"))
            .when(pl.col("timestamp_utc").dt.month().is_in([3, 4, 5]))
            .then(pl.lit("Spring"))
            .when(pl.col("timestamp_utc").dt.month().is_in([6, 7, 8]))
            .then(pl.lit("Summer"))
            .otherwise(pl.lit("Autumn"))
            .alias("season"),
            pl.col("Matched_Events")
            .str.split("; ")
            .list.first()
            .alias("primary_phenom"),
            (pl.col("Matched_Count") > 1).alias("is_multi_hazard"),
            (pl.col("max_rolling_avg") / pl.col("median_sum")).alias(
                "hourly_norm_severity_ratio"
            ),
            pl.when(pl.col("source_completeness_pct") == 100.0)
            .then(pl.lit("100% Complete"))
            .when(pl.col("source_completeness_pct") >= 75.0)
            .then(pl.lit("75% - 99% Complete"))
            .when(pl.col("source_completeness_pct") >= 50.0)
            .then(pl.lit("50% - 74% Complete"))
            .otherwise(pl.lit("< 50% Complete"))
            .alias("completeness_tier"),
        ]
    )

    provenance = {
        "initial_rows": initial_rows,
        "invalid_timestamp_rows_dropped": invalid_ts_rows,
        "implausible_rows_dropped": implausible_rows_removed,
        "duplicate_rows_dropped": duplicate_rows_removed,
        "final_cleaned_rows": int(df_enriched.height),
    }
    return df_enriched, provenance


def clean_availability_dataframe(df: pl.DataFrame) -> tuple[pl.DataFrame, Dict[str, int]]:
    """Clean and standardize EAGLEI_Source_Record_Availability DataFrame."""
    validate_required_columns(df.columns, AVAILABILITY_REQUIRED_COLS, "Availability")
    initial_rows = df.height
    if initial_rows == 0:
        raise ValueError("Input Availability DataFrame is empty.")

    df_parsed = df.with_columns(
        pl.col("Date").str.to_date("%m/%d/%Y", strict=False).alias("date_parsed")
    )
    invalid_dates = int(df_parsed.filter(pl.col("date_parsed").is_null()).height)
    df_valid = df_parsed.filter(pl.col("date_parsed").is_not_null())

    df_dedup = df_valid.unique(
        subset=["fips_code", "date_parsed"], keep="first", maintain_order=True
    )
    dups_removed = int(df_valid.height - df_dedup.height)

    df_enriched = df_dedup.with_columns(
        [
            pl.col("date_parsed").dt.year().cast(pl.Int32).alias("year"),
            pl.col("date_parsed").dt.month().cast(pl.Int32).alias("month"),
            (pl.col("fips_code") // 1000).cast(pl.Int32).alias("state_fips"),
            pl.when(pl.col("observed_15min_records") == 0)
            .then(pl.lit("Reporting Gap (0% Observed)"))
            .when(pl.col("source_record_availability_pct") < 50.0)
            .then(pl.lit("< 50% Complete"))
            .when(pl.col("source_record_availability_pct") < 75.0)
            .then(pl.lit("50% - 74% Complete"))
            .when(pl.col("source_record_availability_pct") < 100.0)
            .then(pl.lit("75% - 99% Complete"))
            .otherwise(pl.lit("100% Complete"))
            .alias("coverage_category"),
        ]
    )

    provenance = {
        "initial_rows": initial_rows,
        "invalid_date_rows_dropped": invalid_dates,
        "duplicate_rows_dropped": dups_removed,
        "final_cleaned_rows": int(df_enriched.height),
    }
    return df_enriched, provenance


def summarize_nws_warnings_dataframe(df: pl.DataFrame) -> tuple[pl.DataFrame, Dict[str, int]]:
    """Standardize mixed timestamp formats and build an aggregated WFO-Year-Phenomenon summary table from NWS warnings."""
    initial_rows = df.height
    # Extract 4-digit year robustly across both 'YYYY-MM-DD HH:MM' and 'M/D/YYYY H:MM' formats
    df_with_yr = df.with_columns(
        [
            pl.col("ISSUED")
            .str.extract(r"(\d{4})", 1)
            .cast(pl.Int32, strict=False)
            .alias("issue_year"),
            pl.when(pl.col("WINDTAG").is_not_null() & (pl.col("WINDTAG") != "None") & (pl.col("WINDTAG") != ""))
            .then(pl.col("WINDTAG").cast(pl.Float64, strict=False))
            .otherwise(None)
            .alias("wind_mph"),
            pl.when(pl.col("HAILTAG").is_not_null() & (pl.col("HAILTAG") != "None") & (pl.col("HAILTAG") != ""))
            .then(pl.col("HAILTAG").cast(pl.Float64, strict=False))
            .otherwise(None)
            .alias("hail_in"),
            (
                pl.col("TORNADOTAG").is_not_null()
                & (pl.col("TORNADOTAG") != "None")
                & (pl.col("TORNADOTAG") != "")
            ).alias("has_tornado_tag"),
            (
                pl.col("DAMAGETAG").is_not_null()
                & (pl.col("DAMAGETAG") != "None")
                & (pl.col("DAMAGETAG") != "")
            ).alias("has_damage_tag"),
        ]
    )

    valid_df = df_with_yr.filter(pl.col("issue_year").is_not_null())
    summary_df = (
        valid_df.group_by(["WFO", "issue_year", "PHENOM", "SIG", "GTYPE"])
        .agg(
            [
                pl.len().alias("vtec_action_rows"),
                pl.col("ETN").n_unique().alias("unique_etn_numbers"),
                pl.col("AREA_KM2").median().round(2).alias("median_area_km2"),
                pl.col("AREA_KM2").mean().round(2).alias("mean_area_km2"),
                pl.col("IS_EMERGENCY").sum().alias("emergency_rows"),
                pl.col("wind_mph").max().alias("max_wind_mph"),
                pl.col("hail_in").max().alias("max_hail_in"),
                pl.col("has_tornado_tag").sum().alias("tornado_tagged_rows"),
                pl.col("has_damage_tag").sum().alias("damage_tagged_rows"),
            ]
        )
        .sort(["issue_year", "WFO", "PHENOM"])
    )

    provenance = {
        "initial_nws_rows": initial_rows,
        "valid_year_rows": int(valid_df.height),
        "aggregated_summary_rows": int(summary_df.height),
    }
    return summary_df, provenance


def run_preprocessing_stage(config: Optional[GridPulseConfig] = None) -> Dict[str, Any]:
    """Run Stage 2: Clean datasets, track provenance, and save processed Parquet tables."""
    cfg = config or GridPulseConfig()

    # 1. Clean EAGLE-I VTEC hourly table
    raw_eagle = pl.read_csv(cfg.eagle_vtec_path, infer_schema_length=10000)
    clean_eagle, eagle_prov = clean_eagle_vtec_dataframe(raw_eagle)
    eagle_pq = save_parquet_atomic(
        clean_eagle, cfg.processed_dir / "eagle_vtec_hourly_clean.parquet"
    )

    # 2. Clean Availability table
    raw_avail = pl.read_csv(cfg.availability_path)
    clean_avail, avail_prov = clean_availability_dataframe(raw_avail)
    avail_pq = save_parquet_atomic(
        clean_avail, cfg.processed_dir / "source_availability_clean.parquet"
    )

    # 3. Clean Sensitivity table
    raw_sens = pl.read_csv(cfg.sensitivity_path)
    validate_required_columns(raw_sens.columns, SENSITIVITY_REQUIRED_COLS, "Sensitivity")
    sens_pq = save_parquet_atomic(
        raw_sens, cfg.processed_dir / "missing_data_sensitivity.parquet"
    )

    # 4. Summarize NWS Warnings table
    raw_nws = pl.read_csv(
        cfg.nws_warnings_path, infer_schema_length=10000, ignore_errors=True
    )
    nws_summary, nws_prov = summarize_nws_warnings_dataframe(raw_nws)
    nws_pq = save_parquet_atomic(
        nws_summary, cfg.processed_dir / "nws_warnings_summary.parquet"
    )

    provenance_report = {
        "eagle_vtec_provenance": eagle_prov,
        "availability_provenance": avail_prov,
        "nws_warnings_provenance": nws_prov,
        "parquet_artifacts": {
            "eagle_vtec_hourly_clean": str(eagle_pq),
            "source_availability_clean": str(avail_pq),
            "missing_data_sensitivity": str(sens_pq),
            "nws_warnings_summary": str(nws_pq),
        },
    }

    with open(cfg.metrics_dir / "preprocessing_provenance.json", "w", encoding="utf-8") as f:
        json.dump(provenance_report, f, indent=2)

    return provenance_report
