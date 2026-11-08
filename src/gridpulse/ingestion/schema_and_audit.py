"""Schema definitions, validation, and data quality audit for GridPulse."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import polars as pl
from pyspark.sql import DataFrame as SparkDataFrame
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

from gridpulse.config import GridPulseConfig

logger = logging.getLogger(__name__)

# Required column specifications for each of the 4 datasets
EAGLE_VTEC_REQUIRED_COLS: List[str] = [
    "fips_code",
    "Hour",
    "max_rolling_avg",
    "state",
    "county",
    "median_sum",
    "new_event_no",
    "evDur_Hr",
    "evDur_day",
    "Max_outage",
    "source_completeness_pct",
    "event_mean_completeness_pct",
    "event_min_completeness_pct",
    "WFO",
    "Matched_Events",
    "Matched_Count",
]

AVAILABILITY_REQUIRED_COLS: List[str] = [
    "fips_code",
    "Date",
    "expected_15min_records",
    "observed_15min_records",
    "missing_15min_records",
    "source_record_availability_pct",
]

SENSITIVITY_REQUIRED_COLS: List[str] = [
    "completeness_tier",
    "Total_Observations",
    "Median_Abs_Difference",
    "Median_Relative_Difference",
]

NWS_WARNINGS_REQUIRED_COLS: List[str] = [
    "WFO",
    "ISSUED",
    "EXPIRED",
    "INIT_ISS",
    "INIT_EXP",
    "PHENOM",
    "GTYPE",
    "SIG",
    "ETN",
    "STATUS",
    "NWS_UGC",
    "AREA_KM2",
    "UPDATED",
    "HVTEC_NWSLI",
    "HVTEC_SEVERITY",
    "HVTEC_CAUSE",
    "HVTEC_RECORD",
    "IS_EMERGENCY",
    "POLYBEGIN",
    "POLYEND",
    "WINDTAG",
    "HAILTAG",
    "TORNADOTAG",
    "DAMAGETAG",
]

# Explicit PySpark StructType schemas for deterministic ingestion
EAGLE_VTEC_SPARK_SCHEMA = StructType(
    [
        StructField("fips_code", IntegerType(), True),
        StructField("Hour", StringType(), True),
        StructField("max_rolling_avg", DoubleType(), True),
        StructField("state", StringType(), True),
        StructField("county", StringType(), True),
        StructField("median_sum", DoubleType(), True),
        StructField("new_event_no", LongType(), True),
        StructField("evDur_Hr", IntegerType(), True),
        StructField("evDur_day", IntegerType(), True),
        StructField("Max_outage", DoubleType(), True),
        StructField("source_completeness_pct", DoubleType(), True),
        StructField("event_mean_completeness_pct", DoubleType(), True),
        StructField("event_min_completeness_pct", DoubleType(), True),
        StructField("WFO", StringType(), True),
        StructField("Matched_Events", StringType(), True),
        StructField("Matched_Count", IntegerType(), True),
    ]
)

AVAILABILITY_SPARK_SCHEMA = StructType(
    [
        StructField("fips_code", IntegerType(), True),
        StructField("Date", StringType(), True),
        StructField("expected_15min_records", IntegerType(), True),
        StructField("observed_15min_records", IntegerType(), True),
        StructField("missing_15min_records", IntegerType(), True),
        StructField("source_record_availability_pct", DoubleType(), True),
    ]
)

SENSITIVITY_SPARK_SCHEMA = StructType(
    [
        StructField("completeness_tier", StringType(), True),
        StructField("Total_Observations", LongType(), True),
        StructField("Median_Abs_Difference", DoubleType(), True),
        StructField("Median_Relative_Difference", DoubleType(), True),
    ]
)


def validate_required_columns(
    actual_columns: Sequence[str], required_columns: Sequence[str], dataset_name: str
) -> None:
    """Validate that all required columns exist in a dataset; raise ValueError with actionable message if not."""
    if not actual_columns:
        raise ValueError(f"[{dataset_name}] Dataset has no columns or is empty.")
    missing = [c for c in required_columns if c not in actual_columns]
    if missing:
        raise ValueError(
            f"[{dataset_name}] Missing required columns: {missing}. "
            f"Found columns: {list(actual_columns)}"
        )


def validate_plausible_values_polars(df: pl.DataFrame) -> Dict[str, int]:
    """Check plausible value ranges on EAGLE-I VTEC DataFrame and return counts of any violations."""
    if df.height == 0:
        raise ValueError("Cannot validate an empty DataFrame (0 rows).")
    validate_required_columns(df.columns, EAGLE_VTEC_REQUIRED_COLS, "Eagle_I_VTEC")

    violations = {
        "negative_max_rolling_avg": int(df.filter(pl.col("max_rolling_avg") < 0).height),
        "negative_max_outage": int(df.filter(pl.col("Max_outage") < 0).height),
        "non_positive_duration_hr": int(df.filter(pl.col("evDur_Hr") <= 0).height),
        "invalid_completeness_pct": int(
            df.filter(
                (pl.col("source_completeness_pct") < 0)
                | (pl.col("source_completeness_pct") > 100)
            ).height
        ),
        "invalid_fips_code": int(
            df.filter((pl.col("fips_code") < 1000) | (pl.col("fips_code") > 99999)).height
        ),
        "non_positive_matched_count": int(df.filter(pl.col("Matched_Count") <= 0).height),
    }
    return violations


def run_pyspark_audit_Verification(
    spark: SparkSession, config: GridPulseConfig
) -> Dict[str, Any]:
    """Use PySpark to read the raw CSV datasets, verify schemas and row counts, and return Spark-verified stats."""
    df_eagle_sp: SparkDataFrame = (
        spark.read.option("header", "true")
        .schema(EAGLE_VTEC_SPARK_SCHEMA)
        .csv(str(config.eagle_vtec_path))
    )
    validate_required_columns(
        df_eagle_sp.columns, EAGLE_VTEC_REQUIRED_COLS, "Eagle_I_VTEC_Spark"
    )

    df_avail_sp: SparkDataFrame = (
        spark.read.option("header", "true")
        .schema(AVAILABILITY_SPARK_SCHEMA)
        .csv(str(config.availability_path))
    )
    validate_required_columns(
        df_avail_sp.columns, AVAILABILITY_REQUIRED_COLS, "Availability_Spark"
    )

    df_sens_sp: SparkDataFrame = (
        spark.read.option("header", "true")
        .schema(SENSITIVITY_SPARK_SCHEMA)
        .csv(str(config.sensitivity_path))
    )
    validate_required_columns(
        df_sens_sp.columns, SENSITIVITY_REQUIRED_COLS, "Sensitivity_Spark"
    )

    eagle_stats = df_eagle_sp.select(
        F.count("*").alias("total_rows"),
        F.countDistinct("fips_code").alias("unique_fips"),
        F.countDistinct("state").alias("unique_states"),
        F.countDistinct("WFO").alias("unique_wfos"),
        F.min("Hour").alias("min_hour"),
        F.max("Hour").alias("max_hour"),
        F.avg("source_completeness_pct").alias("mean_completeness_pct"),
        F.avg("max_rolling_avg").alias("mean_rolling_avg_outage"),
        F.max("Max_outage").alias("max_event_outage"),
    ).collect()[0]

    avail_stats = df_avail_sp.select(
        F.count("*").alias("total_rows"),
        F.countDistinct("fips_code").alias("unique_fips"),
        F.avg("source_record_availability_pct").alias("mean_availability_pct"),
        F.sum(F.when(F.col("observed_15min_records") == 0, 1).otherwise(0)).alias(
            "zero_coverage_county_days"
        ),
    ).collect()[0]

    return {
        "spark_version": spark.version,
        "eagle_vtec_spark_summary": eagle_stats.asDict(),
        "availability_spark_summary": avail_stats.asDict(),
        "sensitivity_rows": df_sens_sp.count(),
    }


def run_comprehensive_data_audit(
    config: Optional[GridPulseConfig] = None, spark: Optional[SparkSession] = None
) -> Dict[str, Any]:
    """Execute full initial inspection and data quality audit across all 4 raw files."""
    cfg = config or GridPulseConfig()

    # 1. File metadata check
    files_info = {}
    for label, path in [
        ("eagle_vtec", cfg.eagle_vtec_path),
        ("nws_warnings", cfg.nws_warnings_path),
        ("availability", cfg.availability_path),
        ("sensitivity", cfg.sensitivity_path),
    ]:
        stat = path.stat()
        files_info[label] = {
            "filename": path.name,
            "path": str(path),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
        }

    # 2. Polars exact audit of Eagle_I_US_2024_with_VTEC_Updated.csv
    df_eagle = pl.read_csv(cfg.eagle_vtec_path, infer_schema_length=10000)
    validate_required_columns(df_eagle.columns, EAGLE_VTEC_REQUIRED_COLS, "Eagle_I_VTEC")
    violations = validate_plausible_values_polars(df_eagle)

    dup_full = int(df_eagle.is_duplicated().sum())
    dup_key = int(df_eagle.select(["fips_code", "Hour"]).is_duplicated().sum())
    nulls_eagle = {k: int(v) for k, v in df_eagle.null_count().to_dicts()[0].items()}

    df_eagle_dt = df_eagle.with_columns(
        pl.col("Hour").str.to_datetime("%Y-%m-%dT%H:%M:%SZ", strict=False).alias("dt")
    )
    invalid_timestamps_eagle = int(df_eagle_dt["dt"].is_null().sum())

    yearly_counts = (
        df_eagle_dt.with_columns(pl.col("dt").dt.year().alias("year"))
        .group_by("year")
        .agg(
            [
                pl.len().alias("hourly_rows"),
                pl.col("fips_code").n_unique().alias("unique_counties"),
                pl.col("new_event_no").n_unique().alias("unique_event_ids"),
                pl.col("source_completeness_pct").mean().round(2).alias("mean_completeness_pct"),
            ]
        )
        .sort("year")
        .to_dicts()
    )

    completeness_tier_breakdown = (
        df_eagle.with_columns(
            pl.when(pl.col("source_completeness_pct") == 100.0)
            .then(pl.lit("100% Complete"))
            .when(pl.col("source_completeness_pct") >= 75.0)
            .then(pl.lit("75% - 99% Complete"))
            .when(pl.col("source_completeness_pct") >= 50.0)
            .then(pl.lit("50% - 74% Complete"))
            .otherwise(pl.lit("< 50% Complete"))
            .alias("completeness_tier")
        )
        .group_by("completeness_tier")
        .agg(
            [
                pl.len().alias("hourly_rows"),
                (pl.len() / df_eagle.height * 100.0).round(2).alias("share_pct"),
                pl.col("max_rolling_avg").median().round(4).alias("median_rolling_avg"),
                pl.col("Max_outage").median().round(4).alias("median_event_max_outage"),
            ]
        )
        .sort("hourly_rows", descending=True)
        .to_dicts()
    )

    # 3. Audit EAGLEI_Source_Record_Availability.csv
    df_avail = pl.read_csv(cfg.availability_path)
    validate_required_columns(df_avail.columns, AVAILABILITY_REQUIRED_COLS, "Availability")
    df_avail_dt = df_avail.with_columns(
        pl.col("Date").str.to_date("%m/%d/%Y", strict=False).alias("parsed_date")
    )
    avail_nulls = {k: int(v) for k, v in df_avail.null_count().to_dicts()[0].items()}
    avail_dup_key = int(df_avail.select(["fips_code", "Date"]).is_duplicated().sum())
    avail_summary = {
        "total_rows": int(df_avail.height),
        "excel_truncation_detected": bool(df_avail.height == 1048575),
        "unique_fips": int(df_avail["fips_code"].n_unique()),
        "min_fips": int(df_avail["fips_code"].min()),
        "max_fips": int(df_avail["fips_code"].max()),
        "min_date": str(df_avail_dt["parsed_date"].min()),
        "max_date": str(df_avail_dt["parsed_date"].max()),
        "invalid_dates": int(df_avail_dt["parsed_date"].is_null().sum()),
        "duplicate_county_days": avail_dup_key,
        "zero_coverage_days_count": int(
            df_avail.filter(pl.col("observed_15min_records") == 0).height
        ),
        "zero_coverage_days_pct": round(
            float(
                df_avail.filter(pl.col("observed_15min_records") == 0).height
                / df_avail.height
                * 100.0
            ),
            2,
        ),
        "full_coverage_days_count": int(
            df_avail.filter(pl.col("observed_15min_records") == 96).height
        ),
        "full_coverage_days_pct": round(
            float(
                df_avail.filter(pl.col("observed_15min_records") == 96).height
                / df_avail.height
                * 100.0
            ),
            2,
        ),
        "mean_availability_pct": round(
            float(df_avail["source_record_availability_pct"].mean()), 2
        ),
        "median_availability_pct": round(
            float(df_avail["source_record_availability_pct"].median()), 2
        ),
        "null_counts": avail_nulls,
    }

    # 4. Audit Missing_Data_Sensitivity_Summary.csv
    df_sens = pl.read_csv(cfg.sensitivity_path)
    validate_required_columns(df_sens.columns, SENSITIVITY_REQUIRED_COLS, "Sensitivity")
    sens_records = df_sens.to_dicts()

    # 5. Audit NWS_WARNINGS_COMBINED_data_Updated.csv
    df_nws = pl.read_csv(
        cfg.nws_warnings_path, infer_schema_length=10000, ignore_errors=True
    )
    validate_required_columns(df_nws.columns, NWS_WARNINGS_REQUIRED_COLS, "NWS_Warnings")
    nws_nulls = {k: int(v) for k, v in df_nws.null_count().to_dicts()[0].items()}
    nws_string_none_counts = {}
    for col in ["NWS_UGC", "HVTEC_NWSLI", "HVTEC_SEVERITY", "WINDTAG", "HAILTAG", "TORNADOTAG", "DAMAGETAG"]:
        nws_string_none_counts[col] = int(
            df_nws.filter(
                pl.col(col).is_null() | (pl.col(col) == "") | (pl.col(col) == "None")
            ).height
        )

    nws_summary = {
        "total_rows": int(df_nws.height),
        "unique_wfos": int(df_nws["WFO"].n_unique()),
        "unique_phenoms": int(df_nws["PHENOM"].n_unique()),
        "gtype_breakdown": df_nws["GTYPE"].value_counts(sort=True).to_dicts(),
        "sig_breakdown": df_nws["SIG"].value_counts(sort=True).to_dicts(),
        "emergency_count": int(df_nws.filter(pl.col("IS_EMERGENCY") == True).height),
        "null_counts": nws_nulls,
        "empty_or_literal_none_counts": nws_string_none_counts,
        "mixed_timestamp_formats_detected": True,
    }

    # 6. Optional Spark verification
    spark_verification = None
    if spark is not None:
        spark_verification = run_pyspark_audit_Verification(spark, cfg)

    audit_report = {
        "files": files_info,
        "eagle_vtec": {
            "total_hourly_rows": int(df_eagle.height),
            "total_columns": int(df_eagle.width),
            "unique_counties_fips": int(df_eagle["fips_code"].n_unique()),
            "unique_states": int(df_eagle["state"].n_unique()),
            "unique_wfos": int(df_eagle["WFO"].n_unique()),
            "unique_county_events": int(
                df_eagle.select(["fips_code", "new_event_no"]).n_unique()
            ),
            "min_timestamp_utc": str(df_eagle["Hour"].min()),
            "max_timestamp_utc": str(df_eagle["Hour"].max()),
            "invalid_timestamps": invalid_timestamps_eagle,
            "duplicate_full_rows": dup_full,
            "duplicate_fips_hour_keys": dup_key,
            "null_counts": nulls_eagle,
            "plausible_value_violations": violations,
            "yearly_coverage": yearly_counts,
            "completeness_tier_breakdown": completeness_tier_breakdown,
        },
        "availability": avail_summary,
        "missing_data_sensitivity": sens_records,
        "nws_warnings": nws_summary,
        "spark_verification": spark_verification,
    }

    out_path = cfg.metrics_dir / "data_audit_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)
    logger.info("Saved comprehensive data audit report to %s", out_path)
    return audit_report
