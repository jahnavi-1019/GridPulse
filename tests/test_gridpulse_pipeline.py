"""Comprehensive unit and pipeline tests for GridPulse using clearly labelled synthetic test fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gridpulse.analysis.spatiotemporal_and_weather import (
    compute_temporal_patterns,
    compute_weather_associations,
)
from gridpulse.config import GridPulseConfig
from gridpulse.evaluation.metrics import (
    compute_binary_classification_metrics,
    compute_calibration_table,
)
from gridpulse.features.builder import (
    build_county_reliability_profiles,
    build_event_feature_table,
    build_state_reliability_profiles,
)
from gridpulse.ingestion.schema_and_audit import (
    AVAILABILITY_REQUIRED_COLS,
    EAGLE_VTEC_REQUIRED_COLS,
    validate_plausible_values_polars,
    validate_required_columns,
)
from gridpulse.modeling.trainer import (
    CATEGORICAL_FEATURES,
    FORBIDDEN_LEAKAGE_COLS,
    NUMERIC_FEATURES,
    split_temporal_train_val_test,
    verify_no_leakage,
)
from gridpulse.preprocessing.cleaner import (
    clean_availability_dataframe,
    clean_eagle_vtec_dataframe,
)


@pytest.fixture
def synthetic_eagle_df() -> pl.DataFrame:
    """Synthetic fixture clearly labelled as test data for unit testing EAGLE-I VTEC pipeline logic."""
    return pl.DataFrame(
        {
            "fips_code": [1001, 1001, 1001, 1001, 48201, 48201],
            "Hour": [
                "2019-06-10T12:00:00Z",
                "2019-06-10T13:00:00Z",
                "2021-07-15T14:00:00Z",
                "2022-08-20T15:00:00Z",
                "2020-05-01T10:00:00Z",
                "2022-09-01T11:00:00Z",
            ],
            "max_rolling_avg": [10.0, 25.0, 120.0, 5.0, 300.0, 600.0],
            "state": [
                "Alabama",
                "Alabama",
                "Alabama",
                "Alabama",
                "Texas",
                "Texas",
            ],
            "county": [
                "Autauga",
                "Autauga",
                "Autauga",
                "Autauga",
                "Harris",
                "Harris",
            ],
            "median_sum": [8.0, 8.0, 8.0, 8.0, 50.0, 50.0],
            "new_event_no": [101, 101, 202, 303, 404, 505],
            "evDur_Hr": [2, 2, 5, 1, 8, 12],
            "evDur_day": [0, 0, 0, 0, 0, 1],
            "Max_outage": [25.0, 25.0, 150.0, 5.0, 350.0, 800.0],
            "source_completeness_pct": [75.0, 100.0, 100.0, 25.0, 100.0, 87.5],
            "event_mean_completeness_pct": [87.5, 87.5, 100.0, 25.0, 100.0, 87.5],
            "event_min_completeness_pct": [75.0, 75.0, 100.0, 25.0, 100.0, 87.5],
            "WFO": ["BMX", "BMX", "BMX", "BMX", "HGX", "HGX"],
            "Matched_Events": ["SV", "SV; TO", "TO", "HT", "SV", "HU; TR"],
            "Matched_Count": [1, 2, 1, 1, 1, 2],
        }
    )


@pytest.fixture
def synthetic_availability_df() -> pl.DataFrame:
    """Synthetic fixture clearly labelled as test data for source availability logic."""
    return pl.DataFrame(
        {
            "fips_code": [1001, 1001, 1001, 1003],
            "Date": ["1/1/2015", "1/2/2015", "1/3/2015", "1/1/2015"],
            "expected_15min_records": [96, 96, 96, 96],
            "observed_15min_records": [0, 48, 96, 12],
            "missing_15min_records": [96, 48, 0, 84],
            "source_record_availability_pct": [0.0, 50.0, 100.0, 12.5],
        }
    )


def test_schema_and_required_column_validation(synthetic_eagle_df: pl.DataFrame) -> None:
    """1. Test schema and required-column validation."""
    validate_required_columns(
        synthetic_eagle_df.columns, EAGLE_VTEC_REQUIRED_COLS, "Synthetic_Eagle"
    )
    dropped_df = synthetic_eagle_df.drop("Max_outage")
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_required_columns(
            dropped_df.columns, EAGLE_VTEC_REQUIRED_COLS, "Synthetic_Eagle"
        )


def test_timestamp_parsing_and_invalid_timestamps(
    synthetic_eagle_df: pl.DataFrame,
) -> None:
    """2. Test timestamp parsing and filtering of invalid timestamps."""
    bad_row = synthetic_eagle_df.head(1).with_columns(
        pl.lit("NOT_A_VALID_TIMESTAMP").alias("Hour")
    )
    combined = pl.concat([synthetic_eagle_df, bad_row])
    cleaned, prov = clean_eagle_vtec_dataframe(combined)
    assert prov["invalid_timestamp_rows_dropped"] == 1
    assert cleaned.height == synthetic_eagle_df.height
    assert "timestamp_utc" in cleaned.columns


def test_duplicate_handling(synthetic_eagle_df: pl.DataFrame) -> None:
    """3. Test duplicate (fips_code, Hour) detection and deduplication."""
    dup_df = pl.concat([synthetic_eagle_df, synthetic_eagle_df.head(2)])
    cleaned, prov = clean_eagle_vtec_dataframe(dup_df)
    assert prov["duplicate_rows_dropped"] == 2
    assert cleaned.height == synthetic_eagle_df.height


def test_missingness_and_source_coverage_logic(
    synthetic_availability_df: pl.DataFrame,
) -> None:
    """4. Test missingness and source-coverage categorization (distinguishing 0% reporting gaps from 100% coverage)."""
    cleaned_avail, prov = clean_availability_dataframe(synthetic_availability_df)
    assert prov["final_cleaned_rows"] == 4
    cats = cleaned_avail["coverage_category"].to_list()
    assert "Reporting Gap (0% Observed)" in cats
    assert "100% Complete" in cats
    assert "50% - 74% Complete" in cats
    assert "< 50% Complete" in cats


def test_feature_calculations_and_aggregation_correctness(
    synthetic_eagle_df: pl.DataFrame,
) -> None:
    """5. Test episode aggregation and strictly causal shift(1) historical feature engineering."""
    cleaned, _ = clean_eagle_vtec_dataframe(synthetic_eagle_df)
    events = build_event_feature_table(cleaned, high_severity_threshold=100.0)
    # 6 hourly rows correspond to 5 unique (fips_code, new_event_no) episodes
    assert events.height == 5

    # Check fips_code 1001 episodes (events 101, 202, 303)
    al_events = events.filter(pl.col("fips_code") == 1001).sort("event_start_utc")
    assert al_events.height == 3
    # First event (101) has 2 matched hours, initial_outage_hr1 = 10.0, Max_outage = 25.0
    assert al_events["observed_matched_hours"][0] == 2
    assert al_events["initial_outage_hr1"][0] == 10.0
    assert al_events["Max_outage"][0] == 25.0
    # Second event (202) must see prior_1_max_outage == 25.0 from event 101 (strictly causal)
    assert al_events["prior_1_max_outage"][1] == 25.0
    # Third event (303) must see prior_1_max_outage == 150.0 from event 202
    assert al_events["prior_1_max_outage"][2] == 150.0


def test_geographic_and_temporal_joins_and_profiles(
    synthetic_eagle_df: pl.DataFrame,
) -> None:
    """6. Test geographic profile construction, state metadata enrichment, and temporal aggregations."""
    cleaned, _ = clean_eagle_vtec_dataframe(synthetic_eagle_df)
    events = build_event_feature_table(cleaned)
    cnty_prof = build_county_reliability_profiles(events)
    state_prof = build_state_reliability_profiles(events, cnty_prof)

    assert cnty_prof.height == 2
    assert state_prof.height == 2
    assert set(state_prof["state_abbr"].to_list()) == {"AL", "TX"}

    temp_tables = compute_temporal_patterns(cleaned, events)
    assert temp_tables["temporal_by_hour"]["hourly_records"].sum() == cleaned.height


def test_target_construction_and_leakage_prevention(
    synthetic_eagle_df: pl.DataFrame,
) -> None:
    """7. Test target construction, chronological train/val/test splitting, and leakage rejection."""
    cleaned, _ = clean_eagle_vtec_dataframe(synthetic_eagle_df)
    events = build_event_feature_table(cleaned, high_severity_threshold=100.0)
    train_df, val_df, test_df = split_temporal_train_val_test(
        events, train_end_year=2020, val_year=2021, test_year=2022
    )
    assert int(train_df["year"].max()) <= 2020
    assert int(val_df["year"].min()) == 2021
    assert int(test_df["year"].min()) == 2022

    # Verify that passing a forbidden target/post-onset column raises ValueError
    with pytest.raises(ValueError, match="Data leakage detected"):
        verify_no_leakage(
            NUMERIC_FEATURES + ["Max_outage"], train_df, val_df, test_df
        )


def test_evaluation_metric_calculations() -> None:
    """8. Test binary classification and calibration metric calculations."""
    y_true = np.array([0, 0, 1, 1, 0, 1, 0, 1])
    y_prob = np.array([0.05, 0.20, 0.85, 0.90, 0.15, 0.75, 0.30, 0.40])
    metrics = compute_binary_classification_metrics(y_true, y_prob, threshold=0.5)
    assert 0.85 <= metrics["roc_auc"] <= 1.0
    assert metrics["confusion_matrix"]["tp"] == 3
    assert metrics["confusion_matrix"]["fn"] == 1
    assert metrics["confusion_matrix"]["tn"] == 4
    assert metrics["confusion_matrix"]["fp"] == 0

    cal = compute_calibration_table(y_true, y_prob, n_bins=3)
    assert len(cal) >= 2


def test_empty_data_and_missing_file_handling(tmp_path: Path) -> None:
    """9. Test graceful failure with actionable error messages on empty DataFrames and missing files."""
    empty_df = pl.DataFrame()
    with pytest.raises(ValueError, match="empty"):
        validate_plausible_values_polars(empty_df)

    bad_cfg = GridPulseConfig(
        project_root=tmp_path,
        eagle_vtec_filename="nonexistent_file.csv",
    )
    with pytest.raises(FileNotFoundError, match="Required source file"):
        _ = bad_cfg.eagle_vtec_path
