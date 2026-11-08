"""SparkSession lifecycle and cross-platform Parquet I/O utilities."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import polars as pl
from pyspark.sql import DataFrame as SparkDataFrame
from pyspark.sql import SparkSession

from gridpulse.config import GridPulseConfig

logger = logging.getLogger(__name__)


def get_spark_session(
    config: Optional[GridPulseConfig] = None, app_name: str = "GridPulse_Analytics"
) -> SparkSession:
    """Create or retrieve a configured PySpark session suitable for student machines."""
    cfg = config or GridPulseConfig()
    builder = (
        SparkSession.builder.appName(app_name)
        .master(cfg.spark_master)
        .config("spark.driver.memory", cfg.spark_driver_memory)
        .config("spark.sql.execution.arrow.pyspark.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.showConsoleProgress", "false")
    )
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def read_parquet_spark(spark: SparkSession, path: Path | str) -> SparkDataFrame:
    """Read a Parquet file into a PySpark DataFrame."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Parquet file not found: {p}")
    return spark.read.parquet(str(p))


def save_parquet_atomic(df_pl: pl.DataFrame, path: Path | str) -> Path:
    """Save a Polars/Arrow table as a single atomic Parquet file readable by PySpark and Streamlit."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df_pl.write_parquet(p, compression="zstd")
    logger.info("Saved Parquet file: %s (%d rows, %d cols)", p.name, df_pl.height, df_pl.width)
    return p
