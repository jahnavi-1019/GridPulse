#!/usr/bin/env python
"""CLI entrypoint for running the GridPulse data engineering, analysis, and ML pipeline in stages."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to Python path so gridpulse can be imported without pip install -e .
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gridpulse.analysis.spatiotemporal_and_weather import run_analysis_stage
from gridpulse.config import GridPulseConfig
from gridpulse.features.builder import run_feature_engineering_stage
from gridpulse.ingestion.schema_and_audit import run_comprehensive_data_audit
from gridpulse.modeling.trainer import run_predictive_modeling_stage
from gridpulse.pipeline.orchestrator import generate_figures_and_reports, run_full_pipeline
from gridpulse.preprocessing.cleaner import run_preprocessing_stage
from gridpulse.utils.spark_session import get_spark_session


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="GridPulse — Reproducible PySpark & ML Outage Analytics Pipeline"
    )
    parser.add_argument(
        "--stage",
        choices=["all", "audit", "preprocess", "features", "analyze", "model", "report"],
        default="all",
        help="Pipeline stage to execute (default: all)",
    )
    parser.add_argument(
        "--no-spark",
        action="store_true",
        help="Skip PySpark JVM verification during audit stage if running in constrained environment",
    )
    args = parser.parse_args()

    cfg = GridPulseConfig(project_root=PROJECT_ROOT)

    if args.stage == "all":
        res = run_full_pipeline(cfg, use_spark_audit=not args.no_spark)
        print(json.dumps({"status": res["status"], "elapsed_seconds": res["elapsed_seconds"]}, indent=2))
    elif args.stage == "audit":
        spark = None if args.no_spark else get_spark_session(cfg)
        try:
            res = run_comprehensive_data_audit(cfg, spark=spark)
            print(json.dumps(res["eagle_vtec"], indent=2))
        finally:
            if spark is not None:
                spark.stop()
    elif args.stage == "preprocess":
        res = run_preprocessing_stage(cfg)
        print(json.dumps(res, indent=2))
    elif args.stage == "features":
        res = run_feature_engineering_stage(cfg)
        print(json.dumps(res, indent=2))
    elif args.stage == "analyze":
        res = run_analysis_stage(cfg)
        print(json.dumps(res, indent=2))
    elif args.stage == "model":
        res = run_predictive_modeling_stage(cfg)
        print(json.dumps(res["models"], indent=2))
    elif args.stage == "report":
        res = generate_figures_and_reports(cfg)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
